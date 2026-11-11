"""Returns-only minimum-variance TOOL qualification, not an investment mandate."""
import argparse
import csv
from datetime import date,datetime,timezone
import hashlib
from importlib.metadata import version
import io
import json
import math
from pathlib import Path
import re
import socket
import sys
from zoneinfo import ZoneInfo

import cvxpy as cp
import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier,expected_returns,risk_models

ROOT=Path(__file__).resolve().parent
SOLVER_OPTIONS={'tol_gap_abs':1e-10,'tol_gap_rel':1e-10,'tol_feas':1e-10}


def refuse_network(*args,**kwargs):raise RuntimeError('Network input is disabled in this returns-only command')


def data_path(value,suffix):
    path=(ROOT/value).resolve()
    if not path.is_relative_to(ROOT/'data')or path.suffix!=suffix or not path.is_file():
        raise ValueError('Input must be an existing data/ file with suffix '+suffix)
    return path


def parser():
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--input',required=True);p.add_argument('--metadata',required=True)
    p.add_argument('--periods-per-year',type=int,choices=[252,365],required=True)
    p.add_argument('--return-model',choices=['arithmetic'],required=True)
    p.add_argument('--risk-model',choices=['sample_cov'],required=True)
    p.add_argument('--objective',choices=['min_variance'],required=True)
    p.add_argument('--bounds',choices=['long_only_fully_invested'],required=True)
    p.add_argument('--rf',type=float,choices=[0.0],required=True)
    p.add_argument('--solver',choices=['CLARABEL'],required=True)
    p.add_argument('--output',choices=['results'],default='results')
    return p


def load_input(csv_path,meta_path):
    if csv_path.stat().st_size>10_000_000 or meta_path.stat().st_size>100_000:raise ValueError('CSV limit10MB/metadata100KB')
    raw,mraw=csv_path.read_bytes(),meta_path.read_bytes();meta=json.loads(mraw)
    fields=['dataset_kind','instruments','source','as_of','timezone','return_type','return_basis','frequency','publication_rights']
    if not isinstance(meta,dict)or any(not isinstance(meta.get(k),str)or not meta[k].strip()for k in fields):raise ValueError('Metadata requires nonempty strings: '+','.join(fields))
    if meta['dataset_kind']not in ['synthetic','market']or meta['return_type']!='simple_fractional'or meta['frequency']!='daily_observations':raise ValueError('Declare synthetic/market, simple_fractional and daily_observations')
    zone=ZoneInfo(meta['timezone']);asof=datetime.fromisoformat(meta['as_of'])
    if asof.tzinfo is None or asof.utcoffset()is None:raise ValueError('as_of requires UTC offset')
    reader=csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True);header=next(reader,None)
    if not header or header[0]!='Date'or not 3<=len(header[1:])<=10 or len(set(header))!=len(header)or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}',x)for x in header[1:]):raise ValueError('Header Date then3-10 unique safe asset labels required')
    dates,rows=[],[]
    for row in reader:
        if len(row)!=len(header)or any(not x.strip()for x in row):raise ValueError('Blank/missing/wrong-width input record')
        day=date.fromisoformat(row[0])
        if day.isoformat()!=row[0]or(dates and row[0]<=dates[-1]):raise ValueError('Unique strictly increasing ISO dates required')
        if day>asof.astimezone(zone).date():raise ValueError('Date after declared as_of')
        values=[float(x)for x in row[1:]]
        if any(not math.isfinite(x)or not -1<x<1 for x in values):raise ValueError('Finite simple fractional returns strictly -1<r<1 required; no prices/percent/log/bankrupt input')
        dates.append(row[0]);rows.append(values)
    if len(rows)<252:raise ValueError('At least252 daily observations required for this qualification recipe')
    frame=pd.DataFrame(rows,index=pd.DatetimeIndex(dates),columns=header[1:],dtype='float64')
    return frame,meta,hashlib.sha256(raw).hexdigest(),hashlib.sha256(mraw).hexdigest()


def models(frame,frequency):
    sample=frame.cov()*frequency
    eigen=np.linalg.eigvalsh(sample.to_numpy())
    if not np.isfinite(eigen).all()or eigen[-1]<=0 or eigen[0]<=eigen[-1]*1e-8:raise ValueError('Singular/nonpositive/ill-conditioned sample covariance refused; no covariance repair')
    mu=expected_returns.mean_historical_return(frame,returns_data=True,compounding=False,frequency=frequency,log_returns=False)
    cov=risk_models.sample_cov(frame,returns_data=True,frequency=frequency,log_returns=False)
    if not np.array_equal(cov.to_numpy(),sample.to_numpy()):raise ValueError('Upstream covariance changed explicit sample covariance')
    if not np.isfinite(mu.to_numpy()).all():raise ValueError('Nonfinite annual arithmetic estimates')
    return mu,cov


def validate_solution(weights,mu,cov,status):
    w=np.asarray(weights,dtype=float);s=cov.to_numpy();m=mu.to_numpy()
    if status!='optimal':raise ValueError('Only exact optimal solver status accepted, not inaccurate: '+str(status))
    if not np.isfinite(w).all()or abs(float(w.sum())-1)>1e-7 or (w< -1e-7).any()or(w>1+1e-7).any():raise ValueError('Weights violate finite/long-only/fully-invested contract')
    # Convex positive-definite minimum-variance KKT, independent of solver status.
    gradient=2*s@w;free=(w>1e-6)&(w<1-1e-6)
    multiplier=-float(gradient[free].mean())if free.any()else -float(gradient[np.argmax(w)])
    residual=gradient+multiplier
    violation=max(float(np.max(np.abs(residual[free])))if free.any()else 0.,float(np.max(np.maximum(-residual[w<=1e-6],0)))if(w<=1e-6).any()else 0.,float(np.max(np.maximum(residual[w>=1-1e-6],0)))if(w>=1-1e-6).any()else 0.)
    if violation>1e-7:raise ValueError('Independent minimum-variance KKT residual failed')
    variance=float(w@s@w);mean=float(w@m)
    if not math.isfinite(variance)or variance<=0 or not math.isfinite(mean):raise ValueError('Nonfinite/zero portfolio performance')
    equal=np.ones(len(w))/len(w);equal_var=float(equal@s@equal)
    if variance>equal_var+1e-8:raise ValueError('Objective worse than feasible equal weights')
    return {'annual_expected_return_arithmetic':mean,'annual_variance':variance,'annual_volatility':math.sqrt(variance),'sharpe_rf_zero':mean/math.sqrt(variance),'weight_sum':float(w.sum()),'kkt_residual':violation,'equal_weight_annual_variance':equal_var}


def optimize(frame,frequency):
    mu,cov=models(frame,frequency)
    if 'CLARABEL'not in cp.installed_solvers():raise ValueError('Required CLARABEL solver unavailable; no fallback')
    ef=EfficientFrontier(mu,cov,weight_bounds=(0,1),solver='CLARABEL',verbose=False,solver_options=SOLVER_OPTIONS.copy())
    ef.min_volatility()
    if ef._opt.solver_stats.solver_name!='CLARABEL':raise ValueError('Actual solver differs from explicit CLARABEL')
    perf=validate_solution(ef.weights,mu,cov,ef._opt.status)
    upstream=ef.portfolio_performance(verbose=False,risk_free_rate=0.0)
    if not all(math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)for a,b in zip(upstream,[perf['annual_expected_return_arithmetic'],perf['annual_volatility'],perf['sharpe_rf_zero']],strict=True)):raise ValueError('Upstream performance/scalar quadratic calculation mismatch')
    return mu,cov,ef.weights.copy(),perf,{'name':ef._opt.solver_stats.solver_name,'status':ef._opt.status,'iterations':ef._opt.solver_stats.num_iters,'options':SOLVER_OPTIONS}


def run(args):
    socket.socket.connect=refuse_network;socket.create_connection=refuse_network
    frame,meta,ih,mh=load_input(data_path(args.input,'.csv'),data_path(args.metadata,'.json'))
    mu,cov,w,perf,solver=optimize(frame,args.periods_per_year)
    output=ROOT/'results'
    if output.is_symlink():raise ValueError('results must not be symlink')
    output.mkdir(exist_ok=True)
    pd.DataFrame({'Asset':frame.columns,'Weight':w,'AnnualExpectedReturnArithmetic':mu.to_numpy()}).to_csv(output/'weights-and-model.csv',index=False)
    cov.to_csv(output/'annual-sample-covariance.csv',index_label='Asset')
    pd.DataFrame({'Date':frame.index.strftime('%Y-%m-%d'),'InSampleFixedWeightReturn':frame.to_numpy()@w}).to_csv(output/'in-sample-returns.csv',index=False)
    summary={'status':'success','purpose':'TOOL QUALIFICATION ONLY, not an investment mandate/advice/executed portfolio','dataset':meta,'input':args.input,'input_sha256':ih,'metadata_sha256':mh,'observations':len(frame),'assets':list(frame.columns),'start_date':frame.index[0].date().isoformat(),'end_date':frame.index[-1].date().isoformat(),'parameters':{'periods_per_year':args.periods_per_year,'return_model':'arithmetic daily mean * frequency, not compounded CAGR','risk_model':'sample covariance ddof1 * frequency, no shrinkage/repair','objective':'minimize w.T @ annual_cov @ w; expected return NOT objective/target','constraints':'sum(w)=1; 0<=w<=1; no short/leverage, no other investor constraints','rf_annual':0.0},'weights':dict(zip(frame.columns,map(float,w),strict=True)),'performance':perf,'solver':solver,'versions':{n:version(n)for n in ['pyportfolioopt','cvxpy','clarabel','numpy','pandas','scipy']},'python':sys.version,'generated_at':datetime.now(timezone.utc).isoformat(),'limits':'Supplied simple fractional returns, no price/log conversion, missing/date/calendar completion, corporate-action/fee/tax/FX estimates, symbol/network fetch, discrete allocation or trading. In-sample fitted risk/mean estimates, not out-of-sample performance or a backtest. Bounds/objective/models are explicit tool qualification defaults, not user investment constraints. No financial recommendation or Sharia/asset screening claim. Solver weights exported uncleaned, not rounded/renormalized.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    text=meta['dataset_kind'].upper()+' MINIMUM-VARIANCE TOOL QUALIFICATION\n'+summary['purpose']+'\n'+f"{len(frame)} observations, {summary['start_date']} through {summary['end_date']}; {len(w)} assets\n"+json.dumps(summary['parameters'],indent=2)+'\nWeights: '+json.dumps(summary['weights'])+'\nPerformance estimates: '+json.dumps(perf)+'\n'+summary['limits']+'\n'
    (output/'summary.txt').write_text(text);print(text);return summary


def main(argv=None):
    args=parser().parse_args(argv)
    try:run(args)
    except Exception as exc:
        print('Analysis rejected: '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
