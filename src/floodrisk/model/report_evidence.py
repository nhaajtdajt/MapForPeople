# Chép nguyên văn từ flood_prediction_models, commit 842da0a, file src/floodrisk/evidence.py. Không sửa ở đây.
"""Pure live-report evidence updates for an upstream route risk probability."""
from __future__ import annotations
from datetime import timedelta
import math
import pandas as pd

WINDOW=timedelta(minutes=30)

def _status(row):
    s=str(row.get('status','')).strip().lower().replace(' ','_')
    if s in {'flooded','flood','wet','ngap','yes','true','1'}:return 'flooded'
    if s in {'not_flooded','dry','no_flood','khong_ngap','no','false','0'}:return 'not_flooded'
    value=row.get('flooded')
    if value is True:return 'flooded'
    if value is False:return 'not_flooded'
    return None

def deduplicate_user_route(reports):
    """Keep the first report per user-route in each non-overlapping 30-minute window."""
    if not reports:return []
    df=pd.DataFrame(reports).copy();required={'user_id','route_id','timestamp'}
    if not required.issubset(df.columns):raise ValueError(f'reports require {sorted(required)}')
    df['timestamp']=pd.to_datetime(df.timestamp,utc=True,errors='coerce');df=df.dropna(subset=['timestamp','user_id','route_id']).sort_values('timestamp')
    kept=[];last={}
    for row in df.to_dict('records'):
        key=(str(row['user_id']),str(row['route_id']));stamp=row['timestamp']
        if key in last and stamp-last[key]<WINDOW:continue
        last[key]=stamp;kept.append(row)
    return kept

def update_probability(probability,reports,at):
    """Apply decayed evidence as multiplicative odds; official flooded evidence uses x10."""
    p=float(probability)
    if not math.isfinite(p) or not 0<p<1:raise ValueError('probability must be finite and strictly between 0 and 1')
    now=pd.Timestamp(at)
    if now.tzinfo is None:now=now.tz_localize('UTC')
    else:now=now.tz_convert('UTC')
    log_odds=math.log(p/(1-p))
    for row in deduplicate_user_route(reports):
        status=_status(row)
        if status is None:continue
        stamp=row['timestamp']
        if stamp>now:continue
        age_min=max(0.,(now-stamp).total_seconds()/60);weight=.5**(age_min/30.)
        official=bool(row.get('official',False)) or str(row.get('provenance_class','')).lower()=='official_observation'
        factor=(10. if official else 3.) if status=='flooded' else (1./3.)
        log_odds+=math.log(factor)*weight
    return 1./(1.+math.exp(-max(-700.,min(700.,log_odds))))

def displayed_level(reports,at):
    """Most frequently reported active status/depth level; deterministic ties prefer greater severity."""
    now=pd.Timestamp(at)
    if now.tzinfo is None:now=now.tz_localize('UTC')
    else:now=now.tz_convert('UTC')
    counts={}
    for row in deduplicate_user_route(reports):
        stamp=row['timestamp']
        if stamp>now:continue
        status=_status(row)
        if status=='not_flooded':level='none'
        elif status=='flooded':
            depth=pd.to_numeric(row.get('depth_cm'),errors='coerce')
            level='unknown' if pd.isna(depth) else 'light' if depth<10 else 'moderate' if depth<=30 else 'high'
        else:continue
        counts[level]=counts.get(level,0)+1
    if not counts:return None
    severity={'none':0,'light':1,'unknown':2,'moderate':3,'high':4}
    return max(counts,key=lambda k:(counts[k],severity[k],k))
