import copy
import csv
from datetime import date,timedelta
import json
import math
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import analyze
from command_runner import parse_command

COMMAND='python analyze.py --input data/synthetic-returns.csv --metadata data/synthetic-returns.metadata.json --periods-per-year 252 --return-model arithmetic --risk-model sample_cov --objective min_variance --bounds long_only_fully_invested --rf 0 --solver CLARABEL --output results'
META=json.loads((analyze.ROOT/'data/synthetic-returns.metadata.json').read_text())


def scalar_cov(rows,frequency):
    n=len(rows);cols=list(zip(*rows));means=[statistics.mean(x)for x in cols]
    return means,[[sum((row[a]-means[a])*(row[b]-means[b])for row in rows)/(n-1)*frequency for b in range(len(cols))]for a in range(len(cols))]


def solve_scalar(matrix,rhs):
    # Independent small Gaussian elimination, no numpy/cvxpy optimizer.
    a=[list(row)+[v]for row,v in zip(matrix,rhs,strict=True)];n=len(a)
    for i in range(n):
        pivot=max(range(i,n),key=lambda j:abs(a[j][i]));a[i],a[pivot]=a[pivot],a[i]
        divisor=a[i][i];a[i]=[v/divisor for v in a[i]]
        for j in range(n):
            if j!=i:
                factor=a[j][i];a[j]=[v-factor*u for v,u in zip(a[j],a[i],strict=True)]
    return [row[-1]for row in a]


class OptimizationTests(unittest.TestCase):
    def fixture(self):return analyze.load_input(analyze.ROOT/'data/synthetic-returns.csv',analyze.ROOT/'data/synthetic-returns.metadata.json')[0]
    def test_fixture_models_sample_ddof1_and_arithmetic(self):
        f=self.fixture();mu,cov=analyze.models(f,252);means,expected=scalar_cov(f.to_numpy().tolist(),252)
        for i in range(3):
            self.assertAlmostEqual(mu.iloc[i],means[i]*252,places=12)
            for j in range(3):self.assertAlmostEqual(cov.iloc[i,j],expected[i][j],places=12)
    def test_solver_weights_against_inverse_variance(self):
        f=self.fixture();mu,cov,w,perf,solver=analyze.optimize(f,252);expected=[16/21,4/21,1/21]
        for a,b in zip(w,expected,strict=True):self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(solver['name'],'CLARABEL');self.assertEqual(solver['status'],'optimal');self.assertAlmostEqual(sum(w),1,places=7);self.assertTrue(all(0<=x<=1 for x in w))
    def test_independent_gaussian_solution_objective_performance(self):
        f=self.fixture();mu,cov,w,p,_=analyze.optimize(f,252);means,s=scalar_cov(f.to_numpy().tolist(),252);inv=solve_scalar(s,[1]*3);expected=[x/sum(inv)for x in inv]
        for a,b in zip(w,expected,strict=True):self.assertAlmostEqual(a,b,places=6)
        mean=sum(float(x)*means[i]*252 for i,x in enumerate(w));variance=sum(float(w[i])*s[i][j]*float(w[j])for i in range(3)for j in range(3))
        self.assertAlmostEqual(p['annual_expected_return_arithmetic'],mean,places=12);self.assertAlmostEqual(p['annual_variance'],variance,places=12);self.assertAlmostEqual(p['annual_volatility'],math.sqrt(variance),places=12);self.assertAlmostEqual(p['sharpe_rf_zero'],mean/math.sqrt(variance),places=12)
    def test_frequency_changes_estimates_not_minimum_weights(self):
        _,_,w,a,_=analyze.optimize(self.fixture(),252);_,_,z,b,_=analyze.optimize(self.fixture(),365)
        for x,y in zip(w,z,strict=True):self.assertAlmostEqual(x,y,places=6)
        self.assertAlmostEqual(b['annual_variance']/a['annual_variance'],365/252,places=6)
    def test_mu_does_not_change_minimum_variance_objective(self):
        f=self.fixture();_,_,w,_,_=analyze.optimize(f,252);shift=f+np.array([.01,-.02,.03]);_,_,z,_,_=analyze.optimize(shift,252)
        for x,y in zip(w,z,strict=True):self.assertAlmostEqual(x,y,places=6)
    def test_long_only_active_lower_bound(self):
        f=self.fixture();f['SYN_B']=2*(f.SYN_A-.0004)+.2*(f.SYN_B-.0006)+.0006
        _,_,w,p,_=analyze.optimize(f,252)
        for a,b in zip(w,[16/17,0,1/17],strict=True):self.assertAlmostEqual(a,b,places=5)
        self.assertLess(p['kkt_residual'],1e-7)
    def test_missing_solver_no_fallback(self):
        with patch.object(analyze.cp,'installed_solvers',return_value=[]),self.assertRaises(ValueError):analyze.optimize(self.fixture(),252)
    def test_inaccurate_status_refused(self):
        m,c=analyze.models(self.fixture(),252)
        with self.assertRaises(ValueError):analyze.validate_solution([16/21,4/21,1/21],m,c,'optimal_inaccurate')
    def test_invalid_weights_refused(self):
        m,c=analyze.models(self.fixture(),252)
        for w in [[.5,.5,.5],[-.1,.5,.6],[float('nan'),.5,.5],[1.1,-.1,0]]:
            with self.subTest(w=w),self.assertRaises(ValueError):analyze.validate_solution(w,m,c,'optimal')
    def test_feasible_nonoptimal_weights_refused(self):
        m,c=analyze.models(self.fixture(),252)
        with self.assertRaises(ValueError):analyze.validate_solution([1/3]*3,m,c,'optimal')
    def test_singular_and_constant_refused(self):
        f=self.fixture()
        for g in [f.assign(SYN_C=f.SYN_A),f.assign(SYN_B=0.0),f*0]:
            with self.assertRaises(ValueError):analyze.models(g,252)
    def test_covariance_repair_refused(self):
        with patch.object(analyze.risk_models,'sample_cov',side_effect=lambda f,**kw:f.cov()*252+1e-10),self.assertRaises(ValueError):analyze.models(self.fixture(),252)


class InputTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.rows=[[(date(2022,1,1)+timedelta(days=i)).isoformat(),'.01','-.01','.02']for i in range(252)]
    def load(self,rows=None,meta=None,header=None):
        c=self.root/'x.csv';m=self.root/'x.json'
        with c.open('w',newline='')as f:w=csv.writer(f);w.writerow(header or ['Date','A','B','C']);w.writerows(self.rows if rows is None else rows)
        m.write_text(json.dumps(META if meta is None else meta));return analyze.load_input(c,m)
    def test_exact_minimum(self):self.assertEqual(self.load()[0].shape,(252,3))
    def test_short_refused(self):
        with self.assertRaises(ValueError):self.load(self.rows[:-1])
    def test_nonfinite_missing_units_bounds(self):
        for v in ['nan','inf','-inf','',' ','1','-1','2','oops']:
            rows=copy.deepcopy(self.rows);rows[25][1]=v
            with self.subTest(v=v),self.assertRaises(ValueError):self.load(rows)
    def test_bad_duplicate_unsorted_dates(self):
        for v in ['', '2022/01/01','2022-02-30','2022-01-01','2022-1-2']:
            rows=copy.deepcopy(self.rows);rows[25][0]=v
            with self.subTest(v=v),self.assertRaises(ValueError):self.load(rows)
    def test_duplicate_asset_or_invalid_header(self):
        for h in [['Date','A','A','C'],['Close','A','B','C'],['Date','A','B'],['Date','A','B','bad-label']]:
            with self.subTest(h=h),self.assertRaises(ValueError):self.load(header=h)
    def test_blank_record_and_width(self):
        for row in [[],[''],['2022-01-26','.1'],['2022-01-26','.1','.2','.3','.4']]:
            rows=copy.deepcopy(self.rows);rows[25]=row
            with self.assertRaises(ValueError):self.load(rows)
    def test_metadata_contract(self):
        for k in META:
            m=copy.deepcopy(META);del m[k]
            with self.subTest(k=k),self.assertRaises(ValueError):self.load(meta=m)
    def test_asof_offset_future_and_log_refused(self):
        for k,v in [('as_of','2022-01-01T00:00:00+02:00'),('as_of','2026-11-11T07:00:00'),('return_type','log_returns')]:
            m=copy.deepcopy(META);m[k]=v
            with self.subTest(k=k,v=v),self.assertRaises(ValueError):self.load(meta=m)
    def test_command_paths_and_fixed_policy(self):
        self.assertIn('analyze.py',parse_command(COMMAND)[1])
        for cmd in ['', 'echo hi',COMMAND+'; echo hi',COMMAND.replace('data/synthetic-returns.csv','../secret.csv'),COMMAND.replace('--rf 0','--rf .02'),COMMAND.replace('min_variance','max_sharpe'),COMMAND.replace('CLARABEL','OSQP')]:
            with self.subTest(cmd=cmd),self.assertRaises((ValueError,SystemExit)):parse_command(cmd)


if __name__=='__main__':unittest.main()
