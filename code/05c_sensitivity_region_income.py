"""Sensitivity analysis by income group and geographical region (Reviewer 2, point 2).

Addresses possible residual confounding by country characteristics by (a) restricting
the bivariate correlation analysis to the two dominant homogeneous strata
(high-income countries; European-region countries), and (b) adding income tier as an
additional covariate to the indicator + log-GDP OLS models for the primary outcome.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats

SEED = 20260426
N_BOOT = 2000
CONTINUOUS = [
    ("Out-of-pocket expenditure (% CHE)","oop_pct_che"),
    ("Government health expenditure (% CHE)","gov_pct_che"),
    ("Current health expenditure (% GDP)","che_pct_gdp"),
    ("Current health expenditure per capita (PPP USD)","che_pc_ppp_usd"),
    ("Nurses and midwives per 1000 population","nurses_per_1000"),
    ("Physicians per 1000 population","physicians_per_1000"),
    ("GDP per capita (PPP USD)","gdp_pc_ppp_usd"),
    ("Life expectancy at birth (years)","life_expectancy"),
    ("Radiotherapy units per million population","radiotherapy_units_per_million"),
    ("Morphine consumption (mg/capita/year)","morphine_consumption_mg_per_capita"),
]
OUTCOMES = [
    ("brain_all","brain_adult_5yr_pct"),
    ("glioblastoma","glioblastoma_5yr_pct"),
    ("diffuse_anap","diffuse_anap_astro_5yr"),
    ("oligo","oligodendroglioma_5yr"),
]

def bh(p):
    p=np.asarray(p,float); m=~np.isnan(p); pc=p[m]; n=len(pc)
    if n==0: return p
    o=np.argsort(pc); r=pc[o]*n/(np.arange(n)+1)
    q=np.minimum.accumulate(r[::-1])[::-1]; qs=np.empty(n); qs[o]=q
    out=np.full(p.shape,np.nan); out[m]=np.minimum(qs,1.0); return out

def corr(df,yc,xc,rng):
    s=df[[xc,yc]].apply(pd.to_numeric,errors='coerce').dropna(); n=len(s)
    if n<4: return dict(n=n,r=np.nan,p=np.nan,lo=np.nan,hi=np.nan,rho=np.nan,rho_p=np.nan)
    x,y=s[xc].to_numpy(),s[yc].to_numpy()
    r,p=stats.pearsonr(x,y); rho,rp=stats.spearmanr(x,y)
    bs=[]
    idx=np.arange(n)
    for _ in range(N_BOOT):
        j=rng.choice(idx,n,replace=True)
        if len(np.unique(x[j]))<3 or len(np.unique(y[j]))<3: continue
        try: bs.append(stats.pearsonr(x[j],y[j])[0])
        except Exception: pass
    lo,hi=(np.percentile(bs,[2.5,97.5]) if bs else (np.nan,np.nan))
    return dict(n=n,r=r,p=p,lo=lo,hi=hi,rho=rho,rho_p=rp)

def run_stratum(df,mask,name,outdir):
    for oid,yc in OUTCOMES:
        d=df.copy(); d[yc]=pd.to_numeric(d[yc],errors='coerce'); d=d.dropna(subset=[yc])
        d=d[pd.to_numeric(d['concord_flag_less_reliable'],errors='coerce')!=1]
        d=d[mask.reindex(d.index).fillna(False)]
        rng=np.random.default_rng(SEED)
        rows=[]
        for lab,c in CONTINUOUS:
            rr=corr(d,yc,c,rng); rr.update(indicator=lab,column=c); rows.append(rr)
        R=pd.DataFrame(rows)
        R['q_bh_within']=bh(R['p'].values)
        R.to_csv(outdir/f"sensitivity_{name}__{oid}.csv",index=False)
        if oid=='brain_all':
            print(f"[{name}] brain_all n(max)={int(R['n'].max())} min p={np.nanmin(R['p']):.3f} min q={np.nanmin(R['q_bh_within']):.3f}")

def main():
    ap=Path(sys.argv[1]); outdir=Path(sys.argv[2]); outdir.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(ap)
    hic = df['wb_income_2014'].eq('HIC')
    eur = df['who_region'].eq('EUR')
    run_stratum(df,hic,"income_hic",outdir)
    run_stratum(df,eur,"region_eur",outdir)
    # Income-tier adjusted OLS for primary outcome (HIC binary added to indicator+logGDP)
    d=df.copy(); d['brain_adult_5yr_pct']=pd.to_numeric(d['brain_adult_5yr_pct'],errors='coerce')
    d=d.dropna(subset=['brain_adult_5yr_pct'])
    d=d[pd.to_numeric(d['concord_flag_less_reliable'],errors='coerce')!=1]
    d['hic']=d['wb_income_2014'].eq('HIC').astype(int)
    d['log_gdp_pc_ppp_usd']=pd.to_numeric(d['log_gdp_pc_ppp_usd'],errors='coerce')
    rows=[]
    for lab,c in CONTINUOUS:
        if c=='gdp_pc_ppp_usd': continue
        s=d[[c,'brain_adult_5yr_pct','log_gdp_pc_ppp_usd','hic']].apply(pd.to_numeric,errors='coerce').dropna()
        if len(s)<8: continue
        X=sm.add_constant(s[[c,'log_gdp_pc_ppp_usd','hic']]); y=s['brain_adult_5yr_pct']
        m=sm.OLS(y,X).fit(cov_type='HC3')
        rows.append(dict(indicator=lab,column=c,n=len(s),beta=m.params[c],se=m.bse[c],p=m.pvalues[c],
                         beta_hic=m.params['hic'],p_hic=m.pvalues['hic'],r2=m.rsquared))
    pd.DataFrame(rows).to_csv(outdir/"sensitivity_income_adjusted_regression__brain_all.csv",index=False)
    print("income-adjusted OLS written; min p(indicator)=%.3f"%np.nanmin([r['p'] for r in rows]))

if __name__=="__main__":
    main()
