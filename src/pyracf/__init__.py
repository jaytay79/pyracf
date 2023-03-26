import importlib.resources
import json
import pandas as pd 

import math

from varname import nameof

# No mess with my header lines
import pandas.io.formats.excel
pandas.io.formats.excel.ExcelFormatter.header_style = None

import threading
import time
from datetime import datetime

import xlsxwriter

import os


class StoopidException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class RACF:
    
    # Our states
    STATE_BAD     = -1
    STATE_INIT    =  0
    STATE_PARSING =  1
    STATE_READY   =  2

    # Our static values :)
    GPBD_RECORDTYPE    = '0100'
    GPSGRP_RECORDTYPE  = '0101'
    GPMEM_RECORDTYPE   = '0102'
    GPOMVS_RECORDTYPE  = '0120'

    USBD_RECORDTYPE    = '0200'
    USGCON_RECORDTYPE  = '0203'
    USINSTD_RECORDTYPE = '0204'
    USCON_RECORDTYPE   = '0205'
    USTSO_RECORDTYPE   = '0220'
    USOMVS_RECORDTYPE  = '0270'

    DSBD_RECORDTYPE    = '0400'
    DSCACC_RECORDTYPE  = '0402'
    DSACC_RECORDTYPE   = '0404'

    GRBD_RECORDTYPE    = '0500'
    GRMEM_RECORDTYPE   = '0503'
    GRACC_RECORDTYPE   = '0505'



    def __init__(self, irrdbu00=None):

        self._state = self.STATE_INIT

        with importlib.resources.open_text("pyracf", "offsets.json") as file:
            self._offsets = json.load(file)      

        if not irrdbu00:
            self._state = self.STATE_BAD
        else:
            self._irrdbu00 = irrdbu00
            self._state    = self.STATE_INIT
            self._unloadlines = sum(1 for _ in open(self._irrdbu00, errors="ignore"))


        # Running threads
        self.THREAD_COUNT = 0

        # list of parsed record-types
        self._records = {}

        # Better be prepared for all of em :)
        self.GPBD  = []            
        self.GPSGRP = []
        self.GPMEM  = []
        self.GPDFP  = []
        self.GPOMVS  = []
        self.GPOVM  = []
        self.GPTME  = []
        self.GPCSD  = []
        self.USBD  = []
        self.USCAT  = []
        self.USCLA  = []
        self.USINSTD  = []
        self.USGCON  = []
        self.USCERT  = []
        self.USCON = []
        self.USNMAP  = []
        self.USDMAP  = []
        self.USDFP  = []
        self.USTSO  = []
        self.USCICS  = []
        self.USCOPC  = []
        self.USCRSL  = []
        self.USCTSL  = []
        self.USLAN  = []
        self.USOPR  = []
        self.USOPRP  = []
        self.USWRK  = []
        self.USOMVS  = []
        self.USNOPC  = []
        self.USNDOM  = []
        self.USDCE  = []
        self.USOVM  = []
        self.USLNOT  = []
        self.USDNS  = []
        self.USKERB  = []
        self.USPROXY  = []
        self.USEIM  = []
        self.USCSD  = []
        self.DSBD  = []
        self.DSACC  = []
        self.DSCACC = []
        self.DSDFP  = []
        self.GRBD  = []
        self.GRTVOL  = []
        self.GRACC  = []
        self.GRMEM = []
        self.CERTN  = []

    @property
    def status(self):
        seen = 0
        parsed = 0
        start  = "n.a."
        stop   = "n.a."
        speed  = "n.a."
        parsetime = "n.a."

        for r in self._records:
            seen += self._records[r]['seen']
            parsed += self._records[r]['parsed']

        if self._state == self.STATE_BAD:
            status = "Error"
        elif self._state == self.STATE_INIT:
            status = "Initial Object"
        elif self._state == self.STATE_PARSING:
            status = "Still parsing your unload"
            start  = self._starttime
            speed  = seen/((datetime.now() -self._starttime).total_seconds())

        elif self._state == self.STATE_READY:
            status = "Ready"
            start  = self._starttime
            stop   = self._stopttime
            speed  = seen/((self._stopttime - self._starttime).total_seconds())
            parsetime = (self._stopttime - self._starttime).total_seconds()
     


        return {'status': status, 'input-lines': self._unloadlines, 'lines-read': seen, 'lines-parsed': parsed, 'lines-per-second': math.floor(speed), 'parse-time': parsetime}

    def findOffsets(self, recordType):
        for offset in self._offsets:
            if self._offsets[offset]['record-type'] == recordType:
                return json.loads(json.dumps(self._offsets[offset]))
        return False

    def parse_fancycli(self, recordtypes=[GPBD_RECORDTYPE, GPSGRP_RECORDTYPE, GPMEM_RECORDTYPE, GPOMVS_RECORDTYPE, USBD_RECORDTYPE, USCON_RECORDTYPE, '0220', USOMVS_RECORDTYPE, '0400', DSCACC_RECORDTYPE, DSACC_RECORDTYPE, GRBD_RECORDTYPE, GRACC_RECORDTYPE], save_pickles=False, prefix=''):
        print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - parsing {self._irrdbu00}')
        self.parse(recordtypes=recordtypes)
        print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - selected recordtypes: {",".join(recordtypes)}')
        while self._state != self.STATE_READY:
            progress =  math.floor(((sum(r['seen'] for r in self._records.values() if r)) / self._unloadlines) * 63)
            pct = (progress/63) * 100 # not as strange as it seems:)
            done = progress * '▉'
            todo = (63-progress) * ' '
            print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - progress: {done}{todo} ({pct:.2f}%)'.center(80), end="\r")
            time.sleep(0.5)
        # make completed line always show 100% :)
        print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - progress: {63*"▉"} ({100:.2f}%)'.center(80))
        for r in recordtypes:
            print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - recordtype {r} -> {self._records[r]["parsed"]} records parsed')
        print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - total parse time: {(self._stopttime - self._starttime).total_seconds()} seconds')
        if save_pickles:
            self.save_pickles(path=save_pickles,prefix=prefix)
            print(f'{datetime.now().strftime("%y-%m-%d %H:%M:%S")} - Pickle files saved to {save_pickles}')

    def parse(self, recordtypes=[GPBD_RECORDTYPE, GPSGRP_RECORDTYPE, GPMEM_RECORDTYPE, GPOMVS_RECORDTYPE, USBD_RECORDTYPE, USGCON_RECORDTYPE , USINSTD_RECORDTYPE, USCON_RECORDTYPE, USTSO_RECORDTYPE, USOMVS_RECORDTYPE, DSBD_RECORDTYPE, DSCACC_RECORDTYPE, DSACC_RECORDTYPE, GRBD_RECORDTYPE, GRACC_RECORDTYPE]):
        self._starttime = datetime.now()
        pt = threading.Thread(target=self.parse_t,args=(recordtypes,))
        pt.start()
        return True

    def parse_t(self, thingswewant=[GPBD_RECORDTYPE, GPSGRP_RECORDTYPE, GPMEM_RECORDTYPE, GPOMVS_RECORDTYPE, USBD_RECORDTYPE, USGCON_RECORDTYPE , USINSTD_RECORDTYPE, USCON_RECORDTYPE, USTSO_RECORDTYPE, USOMVS_RECORDTYPE, DSBD_RECORDTYPE, DSCACC_RECORDTYPE, DSACC_RECORDTYPE, GRBD_RECORDTYPE, GRACC_RECORDTYPE]):
        # TODO: make this multiple threads (per record-type?)
        self._state = self.STATE_PARSING
        self.THREAD_COUNT += 1
        # TODO: Complete all record-types. Fix offsets.json !
        with open(self._irrdbu00, 'r', encoding="utf-8", errors="replace") as infile:
            for line in infile:
                r = line[:4]
                if r in self._records:
                    self._records[r]['seen'] += 1
                else:
                    self._records[r] = {}
                    self._records[r]['seen'] = 1
                    self._records[r]['parsed'] = 0
                if r in thingswewant:
                    model = self.findOffsets(r)
                    if model:
                        irrmodel = {}
                        for model in model['offsets']:
                            start = int(model['start'])
                            end   = int(model['end'])
                            name  = model['field-name']
                            value = line[start-1:end].strip()
                            irrmodel[name] = str(value) 
                            
                        if r == self.GPBD_RECORDTYPE:
                            self.GPBD.append(irrmodel)
                        if r == self.GPSGRP_RECORDTYPE:
                            self.GPSGRP.append(irrmodel)
                        if r == self.GPMEM_RECORDTYPE:
                            self.GPMEM.append(irrmodel)
                        if r == self.GPOMVS_RECORDTYPE:
                            self.GPOMVS.append(irrmodel)    
                        if r == self.USBD_RECORDTYPE:
                            self.USBD.append(irrmodel)   
                        if r == self.USGCON_RECORDTYPE:
                            self.USGCON.append(irrmodel)
                        if r == self.USINSTD_RECORDTYPE:
                            self.USINSTD.append(irrmodel)
                        if r == self.USCON_RECORDTYPE:
                            self.USCON.append(irrmodel)
                        if r == self.USTSO_RECORDTYPE:
                            self.USTSO.append(irrmodel)                            
                        if r == self.USOMVS_RECORDTYPE:
                            self.USOMVS.append(irrmodel)                            
                        if r == self.DSBD_RECORDTYPE:
                            self.DSBD.append(irrmodel)
                        if r == self.DSCACC_RECORDTYPE:
                            self.DSCACC.append(irrmodel)                                                 
                        if r == self.DSACC_RECORDTYPE:
                            self.DSACC.append(irrmodel)  
                        if r == self.GRBD_RECORDTYPE: 
                            self.GRBD.append(irrmodel)
                        if r == self.GRMEM_RECORDTYPE:
                            self.GRMEM.append(irrmodel)                            
                        if r == self.GRACC_RECORDTYPE:
                            self.GRACC.append(irrmodel)       
                    self._records[r]['parsed'] += 1
        # all models parsed :)

        if self.GPBD_RECORDTYPE in thingswewant:
            self._groups = pd.DataFrame.from_dict(self.GPBD)
        if self.GPSGRP_RECORDTYPE in thingswewant:
            self._subgroups = pd.DataFrame.from_dict(self.GPSGRP)
        if self.GPMEM_RECORDTYPE in thingswewant:
            self._connects = pd.DataFrame.from_dict(self.GPMEM)
        if self.GPOMVS_RECORDTYPE in thingswewant:
            self._groupOMVS = pd.DataFrame.from_dict(self.GPOMVS)  
        if self.USBD_RECORDTYPE in thingswewant:
            self._users = pd.DataFrame.from_dict(self.USBD)     
        if self.USGCON_RECORDTYPE in thingswewant:
            self._groupConnect = pd.DataFrame.from_dict(self.USGCON)                      
        if self.USINSTD_RECORDTYPE in thingswewant:
            self._installdata = pd.DataFrame.from_dict(self.USINSTD)                                  
        if self.USCON_RECORDTYPE in thingswewant:
            self._connectData = pd.DataFrame.from_dict(self.USCON)                      
        if self.USTSO_RECORDTYPE in thingswewant:
            self._userTSO = pd.DataFrame.from_dict(self.USTSO)          
        if self.USOMVS_RECORDTYPE in thingswewant:
            self._userOMVS = pd.DataFrame.from_dict(self.USOMVS)                        
        if self.DSBD_RECORDTYPE in thingswewant:
            self._datasets = pd.DataFrame.from_dict(self.DSBD)
        if self.DSCACC_RECORDTYPE in thingswewant:
            self._datasetPermit = pd.DataFrame.from_dict(self.DSBD)
        if self.DSACC_RECORDTYPE in thingswewant:
            self._datasetAccess = pd.DataFrame.from_dict(self.DSACC)
        if self.GRBD_RECORDTYPE in thingswewant:
            self._generics = pd.DataFrame.from_dict(self.GRBD)
        if self.GRMEM_RECORDTYPE in thingswewant:
            self._genericMembers = pd.DataFrame.from_dict(self.GRMEM)
        if self.GRACC_RECORDTYPE in thingswewant:
            self._genericAccess = pd.DataFrame.from_dict(self.GRACC)
        
        self.THREAD_COUNT -= 1
        if self.THREAD_COUNT == 0:
            self._state = self.STATE_READY         
            self._stopttime = datetime.now()
        return True

    def save_pickle(self, df='', dfname='', path='', prefix=''):
        # Sanity check
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        
        df.to_pickle(f'{path}/{prefix}{dfname}.pickle')


    def save_pickles(self, path='/tmp', prefix=''):
        # Sanity check
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        # Is Path there ?
        if not os.path.exists(path):
            madedir = os.system(f'mkdir -p {path}')
            if madedir != 0:
                raise StoopidException(f'{path} does not exist, and cannot create')
        # Let's save the pickles
        if len(self.GPBD) > 0:
            self.save_pickle(df=self._groups, dfname='GPBD', path=path, prefix=prefix)
        if len(self.GPSGRP) > 0:
            self.save_pickle(df=self._subgroups, dfname='GPSGRP', path=path, prefix=prefix)
        if len(self.GPMEM) > 0:
            self.save_pickle(df=self._connects, dfname='GPMEM', path=path, prefix=prefix)
        if len(self.GPOMVS) > 0:
            self.save_pickle(df=self._groupOMVS, dfname='GPOMVS', path=path, prefix=prefix)  
        if len(self.USBD) > 0:
            self.save_pickle(df=self._users, dfname='USBD', path=path, prefix=prefix)     
        if len(self.USGCON) > 0:
            self.save_pickle(df=self._groupConnect, dfname='USGCON', path=path, prefix=prefix)                      
        if len(self.USINSTD) > 0:
            self.save_pickle(df=self._installdata, dfname='USINSTD', path=path, prefix=prefix)                                  
        if len(self.USCON) > 0:
            self.save_pickle(df=self._connectData, dfname='USCON', path=path, prefix=prefix)                      
        if len(self.USTSO) > 0:
            self.save_pickle(df=self._userTSO, dfname='USTSO', path=path, prefix=prefix)          
        if len(self.USOMVS) > 0:
            self.save_pickle(df=self._userOMVS, dfname='USOMVS', path=path, prefix=prefix)                        
        if len(self.DSBD) > 0:
            self.save_pickle(df=self._datasets, dfname='DSBD', path=path, prefix=prefix)
        if len(self.DSCACC) > 0:
            self.save_pickle(df=self._datasetPermit, dfname='DSBD', path=path, prefix=prefix)
        if len(self.DSACC) > 0:
            self.save_pickle(df=self._datasetAccess, dfname='DSACC', path=path, prefix=prefix)
        if len(self.GRBD) > 0:
            self.save_pickle(df=self._generics, dfname='GRBD', path=path, prefix=prefix)
        if len(self.GRMEM) > 0:
            self.save_pickle(df=self._genericMembers, dfname='GRMEM', path=path, prefix=prefix)
        if len(self.GRACC) > 0:
            self.save_pickle(df=self._genericAccess, dfname='GRACC', path=path, prefix=prefix)

    @property
    def users(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        try:
            return self._users
        except:
            raise StoopidException('No USBD records parsed!')
        
    
    def user(self, userid=None):
        if not userid:
            raise StoopidException('userid not specified...')
        return self._users.loc[self._users.USBD_NAME==userid]

    @property
    def connectData(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._connectData

    @property
    def specials(self):
        return self._users.loc[self._users['USBD_SPECIAL'] == 'YES']

    @property
    def operations(self):
        return self._users.loc[self._users['USBD_OPER'] == 'YES']

    @property
    def auditors(self):
        return self._users.loc[self._users['USBD_AUDITOR'] == 'YES']

    @property
    def revoked(self):
        return self._users.loc[self._users['USBD_REVOKE'] == 'YES']

    @property
    def groups(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        
        return self._groups
    
    def group(self, group=None):
        if not group:
            raise StoopidException('group not specified...')
        return self._groups.loc[self._groups.GPBD_NAME==group]

    @property
    def groupConnect(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._groupConnect

    @property
    def installdata(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._installdata

    @property
    def datasets(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._datasets

    @property
    def datasetPermit(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._datasetPermit

    @property
    def connects(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._connects

    @property
    def subgroups(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._subgroups

    @property
    def datasetAccess(self):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._datasetAccess

    @property
    def uacc_read_datasets(self):
        return self._datasets.loc[self._datasets.DSBD_UACC=="READ"]

    @property
    def generics(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._generics

    @property
    def genericMembers(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._genericMembers    

    @property
    def genericAccess(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._genericAccess
    
    @property
    def userOMVS(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._userOMVS

    @property
    def groupOMVS(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._groupOMVS        

    @property
    def userTSO(self, query=None):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')
        return self._userTSO    
        
    @property
    def orphans(self):
        
        if self._records[DSACC_RECORDTYPE]['parsed'] + self._records[GRACC_RECORDTYPE]['parsed'] == 0:
            raise StoopidException('No dataset/generic access records parsed! (PEBKAM/ID-10T error)')
            
        datasetOrphans = None
        genericOrphans = None

        if self._records[DSACC_RECORDTYPE]['parsed'] > 0:
            self._datasetAccess = self._datasetAccess.assign(inGroups=self._datasetAccess.DSACC_AUTH_ID.isin(self._groups.GPBD_NAME))
            self._datasetAccess = self._datasetAccess.assign(inUsers=self._datasetAccess.DSACC_AUTH_ID.isin(self._users.USBD_NAME))
            datasetOrphans = self._datasetAccess.loc[(self._datasetAccess['inGroups'] == False) & (self._datasetAccess['inUsers'] == False) & (self._datasetAccess['DSACC_AUTH_ID'] != "*") & (self._datasetAccess['DSACC_AUTH_ID'] != "&RACUID")]
        
        if self._records[GRACC_RECORDTYPE]['parsed'] > 0:
                self._genericAccess = self._genericAccess.assign(inGroups=self._genericAccess.GRACC_AUTH_ID.isin(self._groups.GPBD_NAME))
                self._genericAccess = self._genericAccess.assign(inUsers=self._genericAccess.GRACC_AUTH_ID.isin(self._users.USBD_NAME))
                genericOrphans =  self._genericAccess.loc[(self._genericAccess['inGroups'] == False) & (self._genericAccess['inUsers'] == False) & (self._genericAccess['GRACC_AUTH_ID'] != "*") & (self._genericAccess['GRACC_AUTH_ID'] != "&RACUID")]

        return datasetOrphans, genericOrphans

    def xls(self,fileName='irrdbu00.xlsx'):
        if self._state != self.STATE_READY:
            raise StoopidException('Not done parsing yet! (PEBKAM/ID-10T error)')

        if self._records[DSACC_RECORDTYPE]['parsed'] + self._records[GRACC_RECORDTYPE]['parsed'] == 0:
            raise StoopidException('No dataset/generic access records parsed! (PEBKAM/ID-10T error)')

        writer = pd.ExcelWriter(f'{fileName}', engine='xlsxwriter')
        accessLevelFormats = {
                    'N': writer.book.add_format({'bg_color': 'silver'}),
                    'E': writer.book.add_format({'bg_color': 'purple'}),
                    'R': writer.book.add_format({'bg_color': 'yellow'}),
                    'U': writer.book.add_format({'bg_color': 'orange'}),
                    'C': writer.book.add_format({'bg_color': 'red'}),
                    'A': writer.book.add_format({'bg_color': 'red'}),
                    'D': writer.book.add_format({'bg_color': 'cyan'}), 
                    'T': writer.book.add_format({'bg_color': 'orange'}),
                }

        accessLevels = {
                    'NONE': 'N',
                    'EXECUTE': 'E',
                    'READ': 'R',
                    'UPDATE': 'U',
                    'CONTROL': 'C',
                    'ALTER': 'A',
                    'NOTRUST': 'D',
                    'TRUST': 'T'
                }

        format_br = writer.book.add_format({})
        format_br.set_rotation(90)
        format_nr = writer.book.add_format({})
        format_center = writer.book.add_format({})
        format_center.set_align('center')
        format_center.set_align('vcenter')

        ss = datetime.now()

        classes = self.genericAccess.groupby(['GRACC_CLASS_NAME'])
        for c in classes.groups:
            s = datetime.now()
            authIDsInClass = list(self.genericAccess.loc[self.genericAccess.GRACC_CLASS_NAME==c]['GRACC_AUTH_ID'].unique())
            profilesInClass = list(self.genericAccess.loc[self.genericAccess.GRACC_CLASS_NAME==c]['GRACC_NAME'].unique())
            longestProfile = 0
            for p in profilesInClass:
                if len(p) > longestProfile:
                    longestProfile = len(p)
            newdata = {}
            newdata['Profiles'] = []
            for id in authIDsInClass:
                newdata[id] = [None] * len(profilesInClass)
            classdata = classes.get_group(c)
            profiles = classdata.groupby(['GRACC_NAME'])
            for i,p in enumerate(profiles.groups):
                profiledata = profiles.get_group(p)
                newdata['Profiles'].append(p)
                users = profiledata.groupby(['GRACC_AUTH_ID'])
                for u in users.groups:
                    useraccess = users.get_group(u)['GRACC_ACCESS'].values[0]
                    newdata[u][i] = accessLevels[useraccess]
            df1 = pd.DataFrame(newdata)
            df1.to_excel(writer, sheet_name=c, index=False)
            worksheet = writer.sheets[c]
            worksheet.set_row(0, 64, format_br)
            worksheet.set_column(1, len(authIDsInClass)+1, 2, format_center )
            worksheet.set_column(0, 0, longestProfile + 2 )
            worksheet.write(0, 0, 'Profile', format_nr)

            shared_strings = sorted(worksheet.str_table.string_table, key=worksheet.str_table.string_table.get)
            for i in range(len(authIDsInClass)+1):
                for j in range(len(profilesInClass)+1):
                    if i>0 and j>0:
                        rdict = worksheet.table.get(j,None)
                        centry = rdict.get(i,None)
                        if centry:
                            value = shared_strings[centry.string]
                            worksheet.write(j, i, value, accessLevelFormats[value])

        if self._records[DSBD_RECORDTYPE]['parsed'] > 0:
            ss = datetime.now()
            profilesInClass = list(self.datasetAccess['DSACC_NAME'].unique())
            authIDsInClass = list(self.datasetAccess['DSACC_AUTH_ID'].unique())
            authids = 0
            longestProfile = 0
            for p in profilesInClass:
                if len(p) > longestProfile:
                    longestProfile = len(p)
            newdata = {}
            newdata['Profiles'] = []
            for id in authIDsInClass:
                    newdata[id] = [None] * len(profilesInClass)
            profiles = self.datasetAccess.groupby(['DSACC_NAME'])
            for i,p in enumerate(profiles.groups):
                profiledata = profiles.get_group(p)
                newdata['Profiles'].append(p)
                users = profiledata.groupby(['DSACC_AUTH_ID'])
                for u in users.groups:
                    useraccess = users.get_group(u)['DSACC_ACCESS'].values[0]
                    newdata[u][i] = accessLevels[useraccess]

            df1 = pd.DataFrame(newdata)
            df1.to_excel(writer, sheet_name='DATASET', index=False)
            worksheet = writer.sheets['DATASET']
            worksheet.set_row(0, 64, format_br)
            worksheet.set_column(1, len(authIDsInClass)+1, 2, format_center )
            worksheet.set_column(0, 0, longestProfile + 2 )
            worksheet.write(0, 0, 'Profile', format_nr)

            shared_strings = sorted(worksheet.str_table.string_table, key=worksheet.str_table.string_table.get)
            for i in range(len(authIDsInClass)+1):
                for j in range(len(profilesInClass)+1):
                    if i>0 and j>0:
                        rdict = worksheet.table.get(j,None)
                        centry = rdict.get(i,None)
                        if centry:
                            value = shared_strings[centry.string]
                            worksheet.write(j, i, value, accessLevelFormats[value])

        writer.save()   

class IRRDBU(RACF):
    pass