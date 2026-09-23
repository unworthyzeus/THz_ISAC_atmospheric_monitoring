"""ITU-R P.835-7 atmosphere and quality-controlled IGRA weather profiles.

Weather soundings constrain T/P/humidity, not VOC or aerosol composition.
Geopotential IGRA heights are converted to geometric altitude explicitly.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann

GEOPOTENTIAL_RADIUS_M = 6356766.


def state_from_tpe(temperature_k, pressure_pa, water_pressure_pa):
    t, p, e = np.broadcast_arrays(temperature_k, pressure_pa, water_pressure_pa)
    if not all(np.isfinite(a).all() for a in (t,p,e)) or np.any(t<=0) or np.any(p<=0) or np.any((e<0)|(e>=p)):
        raise ValueError('Nonphysical atmospheric state')
    n = 1 + 1e-6*(77.6*(p-e)/100/t + 72*e/100/t + 3.75e5*e/100/t**2)
    return t, p, e/(Boltzmann*t)/1e6, n


@dataclass(frozen=True)
class StandardAtmosphere:
    """P.835-7 Annex 1, 0-100 km geometric altitude, including upper water floor."""
    ground_altitude_m: float = 0.

    @property
    def boundaries_m(self):
        h = np.array([0,11,20,32,47,51,71,84.852])*1000
        z = GEOPOTENTIAL_RADIUS_M*h/(GEOPOTENTIAL_RADIUS_M-h)
        return np.r_[z,91000,100000]-self.ground_altitude_m

    def state(self, altitude_m):
        z = np.asarray(altitude_m,dtype=float)+self.ground_altitude_m
        if not np.isfinite(z).all() or np.any((z<0)|(z>100000)):
            raise ValueError('P.835-7 reference domain is 0-100 km above sea level')
        h = (GEOPOTENTIAL_RADIUS_M*z/(GEOPOTENTIAL_RADIUS_M+z))/1000
        edges = np.array([0,11,20,32,47,51,71])
        tb = np.array([288.15,216.65,216.65,228.65,270.65,270.65,214.65])
        pb = np.array([1013.25,226.3226,54.74980,8.680422,1.109106,.6694167,.03956649])
        lapse = np.array([-6.5,0,1,2.8,0,-2.8,-2.])
        idx = np.minimum(np.searchsorted(edges,h,side='right')-1,6)
        dh=h-edges[idx]; l=lapse[idx]; base=tb[idx]
        t = base+l*dh
        # Keep both branches finite before selection.
        power = 34.1632/np.where(l==0,1,l)
        p = np.where(l==0,pb[idx]*np.exp(-34.1632*dh/base),pb[idx]*(base/t)**power)
        zk=z/1000
        upper_t = np.where(zk<=91,186.8673,
                          263.1905-76.3232*np.sqrt(np.maximum(0,1-((zk-91)/19.9429)**2)))
        upper_p = np.exp(95.571899-4.011801*zk+.06424731*zk**2-.000478966*zk**3+.000001340543*zk**4)
        t=np.where(z>=86000,upper_t,t); p=np.where(z>=86000,upper_p,p)
        rho=np.maximum(7.5*np.exp(-zk/2),2e-6*p*216.7/t)
        return state_from_tpe(t,p*100,rho*t/216.7*100)


@dataclass(frozen=True)
class TabulatedAtmosphere:
    """Interpolated measured weather; no silent extrapolation or gap filling.

    Log pressure/vapour and linear temperature interpolate between retained
    levels. Humidity at or above the detection floor stays positive for logs.
    The input must contain an explicit surface level at relative altitude zero.
    """
    altitude_m: np.ndarray
    temperature_k: np.ndarray
    pressure_pa: np.ndarray
    water_pressure_pa: np.ndarray
    ground_altitude_m: float = 0.

    def __post_init__(self):
        arrays=[np.asarray(getattr(self,name),dtype=float).copy() for name in
                ('altitude_m','temperature_k','pressure_pa','water_pressure_pa')]
        if any(a.ndim!=1 or len(a)!=len(arrays[0]) or not np.isfinite(a).all() for a in arrays):
            raise ValueError('Profile columns must be finite one-dimensional arrays of equal size')
        if len(arrays[0])<3 or abs(arrays[0][0])>1e-8 or np.any(np.diff(arrays[0])<=0) or np.any(np.diff(arrays[2])>=0):
            raise ValueError('Need a surface and increasing heights with decreasing pressures')
        state_from_tpe(*arrays[1:])
        if np.any(arrays[3]<=0):
            raise ValueError('Positive measured vapour pressure required for log interpolation')
        for name,a in zip(('altitude_m','temperature_k','pressure_pa','water_pressure_pa'),arrays):
            a.setflags(write=False); object.__setattr__(self,name,a)

    @property
    def boundaries_m(self):
        return self.altitude_m

    def state(self, altitude_m):
        z=np.asarray(altitude_m,dtype=float)
        if not np.isfinite(z).all() or np.any((z<0)|(z>self.altitude_m[-1])):
            raise ValueError('Requested height outside measured profile; select an explicit extension')
        t=np.interp(z,self.altitude_m,self.temperature_k)
        p=np.exp(np.interp(z,self.altitude_m,np.log(self.pressure_pa)))
        e=np.exp(np.interp(z,self.altitude_m,np.log(self.water_pressure_pa)))
        return state_from_tpe(t,p,e)


@dataclass(frozen=True)
class ExtendedMeasuredAtmosphere:
    """Measured profile joined continuously to P.835 above its highest level.

    The upper continuation is a declared model: temperature offset decays
    over 10 km; pressure is integrated hydrostatically on the continuation;
    vapour mixing ratio joins the P.835 stratospheric floor over 10 km.
    It is never labelled an observation.
    """
    measured: TabulatedAtmosphere

    @property
    def boundaries_m(self):
        return np.unique(np.r_[self.measured.boundaries_m,
                               StandardAtmosphere(self.measured.ground_altitude_m).boundaries_m])

    def state(self, altitude_m):
        from scipy.integrate import cumulative_trapezoid
        z=np.asarray(altitude_m,dtype=float)
        top=self.measured.altitude_m[-1]
        standard=StandardAtmosphere(self.measured.ground_altitude_m)
        t,p,w,n=standard.state(z)
        inside=z<=top
        mt,mp,mw,mn=self.measured.state(np.minimum(z,top))
        if np.any(~inside):
            ts,ps,ws,_=standard.state(np.array([top]))
            ttop=self.measured.temperature_k[-1]; ptop=self.measured.pressure_pa[-1]
            grid=np.unique(np.r_[top,np.arange(top,float(z.max())+50,50),z[~inside]])
            grid=grid[grid<=z.max()]
            tg=standard.state(grid)[0]+(ttop-ts[0])*np.exp(-(grid-top)/10000)
            gravity=9.80665*(GEOPOTENTIAL_RADIUS_M/(GEOPOTENTIAL_RADIUS_M+grid+self.measured.ground_altitude_m))**2
            logp=np.log(ptop)-cumulative_trapezoid(gravity*.0289644/(8.314462618*tg),grid,initial=0)
            pu=np.exp(np.interp(z[~inside],grid,logp))
            tu=t[~inside]+(ttop-ts[0])*np.exp(-(z[~inside]-top)/10000)
            qtop=self.measured.water_pressure_pa[-1]/ptop
            qu=2e-6+(qtop-2e-6)*np.exp(-(z[~inside]-top)/10000)
            t=np.array(t);p=np.array(p);w=np.array(w);n=np.array(n)
            t[~inside],p[~inside],w[~inside],n[~inside]=state_from_tpe(tu,pu,qu*pu)
        return tuple(np.where(inside,a,b) for a,b in zip((mt,mp,mw,mn),(t,p,w,n)))


def parse_igra_soundings(text):
    """Read IGRA 2.2 fixed-width P/GPH/T/DPDP, retaining QA flags.

    Rows with missing/QC-removed fields are excluded, never set to zero.
    Vapour pressure is derived from reported dew point via Bolton's expression.
    """
    records=[]; context=None
    for line in text.splitlines():
        if line.startswith('#'):
            hour=int(line[24:26])
            context=None if hour==99 else dict(station=line[1:12],
                datetime=f'{line[13:17]}-{line[18:20]}-{line[21:23]}T{hour:02d}:00:00Z')
        elif context and len(line)>=39:
            p=int(line[9:15]); h=int(line[16:21]); temp=int(line[22:27]); dpdp=int(line[34:39])
            if min(p,h,temp,dpdp)<=-8888 or p<=0 or h<0 or dpdp<0:
                continue
            t=temp/10+273.15; td=temp/10-dpdp/10
            e=611.2*np.exp(17.67*td/(td+243.5))
            if not 150<t<340 or not 0<e<p:
                continue
            z=GEOPOTENTIAL_RADIUS_M*h/(GEOPOTENTIAL_RADIUS_M-h)
            records.append({**context,'geopotential_height_m':h,'geometric_altitude_m':z,
                'temperature_k':t,'pressure_pa':p,'water_pressure_pa':e,
                'surface':line[1]=='1','pressure_flag':line[15],'height_flag':line[21],'temperature_flag':line[27]})
    return pd.DataFrame(records)


def sounding_atmosphere(frame):
    data=frame.sort_values('geometric_altitude_m').drop_duplicates('geometric_altitude_m')
    if not data.iloc[0]['surface']:
        raise ValueError('Sounding lacks a complete surface T/P/dew-point record')
    if np.any(np.diff(data.pressure_pa)>=0):
        raise ValueError('Sounding has nonmonotone pressure')
    base=float(data.iloc[0].geometric_altitude_m)
    return TabulatedAtmosphere(data.geometric_altitude_m.to_numpy()-base,
        data.temperature_k.to_numpy(),data.pressure_pa.to_numpy(),data.water_pressure_pa.to_numpy(),base)
