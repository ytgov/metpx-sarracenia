#!/usr/bin/python3
#
# This file is part of sarracenia.
# The sarracenia suite is Free and is proudly provided by the Government of Canada
# Copyright (C) Her Majesty The Queen in Right of Canada, Environment Canada, 2008-2015
#
# Questions or bugs report: dps-client@ec.gc.ca
# sarracenia repository: git://git.code.sf.net/p/metpx/git
# Documentation: http://metpx.sourceforge.net/#SarraDocumentation
#
# sr_message.py : python3 utility tools for sarracenia amqp message processing
#
#
# Code contributed by:
#  Michel Grenier - Shared Services Canada
#  Jun Hu         - Shared Services Canada
#  Last Changed   : Sep 22 10:41:32 EDT 2015
#  Last Revision  : Sep 22 10:41:32 EDT 2015
#
########################################################################
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful, 
#  but WITHOUT ANY WARRANTY; without even the implied warranty of 
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#
#

import calendar,os,socket,sys,time,urllib,urllib.parse

try :
         from sr_util         import *
except :
         from sarra.sr_util    import *

class sr_message():

    def __init__(self,logger):
        self.logger        = logger
        self.amqp_log      = None
        self.amqp_pub      = None
        self.exchange      = None
        self.exchange_pub  = None
        self.topic         = None
        self.notice        = None
        self.headers       = {}

        self.partstr       = None
        self.sumstr        = None
        self.sumflg        = None

        self.part_ext      = 'Part'

        self.chkclass      = Checksum()

        self.bufsize       = 10 * 1024 * 1024

        self.inplace       = True

        self.user          = None

        self.host          = socket.getfqdn()

    def change_partflg(self, partflg ):
        self.partflg       =  partflg 
        self.partstr       = '%s,%d,%d,%d,%d' %\
                             (partflg,self.chunksize,self.block_count,self.remainder,self.current_block)

    def checksum_match(self):
        if not os.path.isfile(self.local_file) : return False
        if self.sumflg in ['0','n']            : return False

        self.compute_local_checksum()

        return self.local_checksum == self.checksum

    def compute_local_checksum(self):
        self.local_checksum = self.compute_chksum(self.local_file,self.local_offset,self.length)

    def from_amqplib(self, msg ):

        self.start_timer()

        #self.logger.debug("attributes= %s" % vars(msg))
        self.exchange  = msg.delivery_info['exchange']
        self.topic     = msg.delivery_info['routing_key']
        self.headers   = msg.properties['application_headers']
        self.notice    = msg.body

        if type(msg.body) == bytes :
           self.notice = msg.body.decode("utf-8")
  
        self.partstr     = None
        self.sumstr      = None

        token        = self.topic.split('.')
        self.version = token[0]

        if self.version == 'v00' :
           self.parse_v00_post()

        if self.version == 'v02' :
           self.parse_v02_post()

    def get_elapse(self):
        return time.time()-self.tbegin

    def log_amqp(self):
        self.log_topic    = self.topic.replace('.post.','.log.')
        self.log_notice   = "%s %d %s %s %f" % \
                       (self.notice,self.code,self.host,self.user,self.get_elapse())
        self.headers['message'] = self.message

        if self.amqp_log != None :
           log_exchange = 'xlog'
           self.amqp_log.publish(log_exchange,self.log_topic,self.log_notice,self.headers)


    def log_error(self):
        self.log_amqp()

        if self.logger   != None :
           self.set_hdrstr()
           self.logger.error("%d %s : %s %s %s" % (self.code,self.message,self.log_topic,self.log_notice,self.hdrstr))

        del self.headers['message']

    def log_info(self):
        self.log_amqp()

        if self.logger   != None :
           self.set_hdrstr()
           self.logger.info("%d %s : %s %s %s" % (self.code,self.message,self.log_topic,self.log_notice,self.hdrstr))

        del self.headers['message']

    def parse_v00_post(self):
        token             = self.topic.split('.')
        # v00             = token[0]
        # dd              = token[1]
        # notify          = token[2]
        self.version      = 'v02'
        self.mtype        = 'post'
        self.topic_prefix = 'v02.post'
        self.subtopic     = '.'.join(token[3:])
        self.topic        = self.topic_prefix + '.' + self.subtopic

        token        = self.notice.split(' ')
        url          = urllib.parse.urlparse(token[2]+token[3])
        self.set_notice(url)
        
        self.checksum = token[0]
        self.filesize = int(token[1])

        self.filename = self.headers['filename']

        self.headers['source'] = 'metpx'

        self.partstr = '1,%d,1,0,0' % self.filesize
        self.headers['parts'] = self.partstr

        self.sumstr  = 'd,%s' % self.checksum
        self.headers['sum'] = self.sumstr

        self.to_clusters = ['ALL']
        self.headers['to_clusters'] = 'ALL'

        self.suffix  = ''
        
        self.set_parts_str(self.partstr)
        self.set_sum_str(self.sumstr)
        self.set_suffix()
        self.set_hdrstr()

    def parse_v02_post(self):

        token         = self.topic.split('.')
        self.version  = token[0]
        self.mtype    = token[1]
        self.topic_prefix = '.'.join(token[:2])
        self.subtopic     = '.'.join(token[3:])

        token        = self.notice.split(' ')
        self.time    = token[0]
        self.url     = urllib.parse.urlparse(token[1]+token[2])
        self.path    = token[2]

        if self.mtype == 'log' :
           self.log_code   = int(token[3])
           self.log_host   = token[4]
           self.log_user   = token[5]
           self.log_elapse = float(token[6])

        self.partstr = None
        if 'parts'   in self.headers :
           self.partstr  = self.headers['parts']

        self.sumstr  = None
        if 'sum'     in self.headers :
           self.sumstr   = self.headers['sum']

        self.to_clusters = []
        if 'to_clusters' in self.headers :
           self.to_clusters  = self.headers['to_clusters'].split(',')

        self.suffix = ''

        self.set_parts_str(self.partstr)
        self.set_sum_str(self.sumstr)
        self.set_suffix()
        self.set_msg_time()
        self.set_hdrstr()

    def part_suffix(self):
        return '.%d.%d.%d.%d.%s.%s' %\
               (self.chunksize,self.block_count,self.remainder,self.current_block,self.sumflg,self.part_ext)

    def publish(self):
        if self.amqp_pub != None :
           self.amqp_pub.publish(self.exchange_pub,self.topic,self.notice,self.headers)
        self.log_info()

    def set_from_cluster(self,from_cluster=None):
        if from_cluster != None :
           self.headers['from_cluster'] = from_cluster
        elif 'from_cluster' in self.headers :
           del self.headers['from_cluster']

    def set_exchange(self,name):
        self.exchange = name

    def set_flow(self,flow=None):
        if flow != None :
           self.headers['flow'] = flow
        elif 'flow' in self.headers :
           del self.headers['flow']

    def set_hdrstr(self):
        self.hdrstr  = ''

        if self.partstr != None :
           self.headers['parts']   = self.partstr
           self.hdrstr  += '%s=%s ' % ('parts',self.partstr)

        if self.sumstr  != None :
           self.headers['sum']     = self.sumstr
           self.hdrstr  += '%s=%s ' % ('sum',self.sumstr)

        if 'from_cluster' in self.headers :
           self.hdrstr  += '%s=%s ' % ('from_cluster',self.headers['from_cluster'])

        if 'source' in self.headers :
           self.hdrstr  += '%s=%s ' % ('source',self.headers['source'])

        if 'to_clusters' in self.headers :
           self.hdrstr  += '%s=%s ' % ('to_clusters',self.headers['to_clusters'])

        if 'flow' in self.headers :
           self.hdrstr  += '%s=%s ' % ('flow',self.headers['flow'])

        if 'rename' in self.headers :
           self.hdrstr  += '%s=%s ' % ('rename',self.headers['rename'])

        if 'message' in self.headers :
           self.hdrstr  += '%s=%s ' % ('message',self.headers['message'])

        # added for v00 compatibility (old version of sr_subscribe)
        # can be taken off when v02 will be fully deployed and end user uses new sr_subscribe
        self.headers['filename'] = os.path.basename(self.url.path).split(':')[0]


    # Once we know the local file we want to use
    # we can have a few flavor of it

    def set_local(self,inplace,local_file,local_url):

        self.inplace       = inplace

        self.local_file    = local_file
        self.local_url     = local_url
        self.local_offset  = 0
        self.in_partfile   = False
        self.local_checksum= None

        # file to file

        if self.partflg == '1' : return

        # part file never inserted

        if not self.inplace :

           self.in_partfile = True

           # part file to part file

           if self.partflg == 'p' : return

           # file inserts to part file

           if self.partflg == 'i' :
              self.local_file = local_file + self.suffix
              self.local_url  = urllib.parse.urlparse( local_url.geturl() + self.suffix )
              return

        
        # part file inserted

        if self.inplace :

           # part file inserts to file (maybe in file, maybe in part file)

           if self.partflg == 'p' :
              self.target_file  = local_file.replace(self.suffix,'')
              self.target_url   = urllib.parse.urlparse( local_url.geturl().replace(self.suffix,''))
              part_file    = local_file
              part_url     = local_url

        
           # file insert inserts into file (maybe in file, maybe in part file)

           if self.partflg == 'i' :
              self.target_file  = local_file
              self.target_url   = local_url
              part_file    = local_file + self.suffix
              part_url     = urllib.parse.urlparse( local_url.geturl() + self.suffix )

           # default setting : redirect to temporary part file

           self.local_file  = part_file
           self.local_url   = part_url
           self.in_partfile = True
        
           # try to make this message a file insert

           # file exists
           if os.path.isfile(self.target_file) :
              self.logger.debug("local_file exists")
              lstat   = os.stat(self.target_file)
              fsiz    = lstat[stat.ST_SIZE] 

              self.logger.debug("offset vs fsiz %d %d" % (self.offset,fsiz ))
              # part/insert can be inserted 
              if self.offset <= fsiz :
                 self.logger.debug("insert")
                 self.local_file   = self.target_file
                 self.local_url    = self.target_url
                 self.local_offset = self.offset
                 self.in_partfile  = False
                 return

              # in temporary part file
              self.logger.debug("exist but no insert")
              return


           # file does not exists but first part/insert ... write directly to local_file
           elif self.current_block == 0 :
              self.logger.debug("not exist but first block")
              self.local_file  = self.target_file
              self.local_url   = self.target_url
              self.in_partfile = False
              return

           # file does not exists any other part/insert ... put in temporary part_file
           else :
              self.logger.debug("not exist and not first block")
              self.in_partfile = True
              return
                 
        # unknow conditions

        self.logger.error("bad unknown conditions")
        return

    def set_msg_time(self):
        parts       = self.time.split('.')
        ts          = time.strptime(parts[0], "%Y%m%d%H%M%S" )
        ep_msg      = calendar.timegm(ts)
        self.tbegin = ep_msg + int(parts[1]) / 1000.0

    def set_notice(self,url,time=None):
        self.url    = url
        self.time   = time
        if time    == None : self.set_time()
        path        = url.path.strip('/')

        if url.scheme == 'file' :
           self.notice = '%s %s %s' % (self.time,'file:','/'+path)
           return

        urlstr      = url.geturl()
        static_part = urlstr.replace(url.path,'') + '/'

        if url.scheme == 'http' :
           self.notice = '%s %s %s' % (self.time,static_part,path)
           return

        if url.scheme[-3:] == 'ftp'  :
           if url.path[:2] == '//'   : path = '/' + path

        self.notice = '%s %s %s' % (self.time,static_part,path)

    def set_parts(self,partflg='1',chunksize=0, block_count=1, remainder=0, current_block=0):
        self.partflg       =  partflg 
        self.chunksize     =  chunksize
        self.block_count   =  block_count
        self.remainder     =  remainder
        self.current_block =  current_block
        self.partstr       =  None
        if partflg         == None : return
        self.partstr       = '%s,%d,%d,%d,%d' %\
                             (partflg,chunksize,block_count,remainder,current_block)
        self.lastchunk     = current_block == block_count-1

    def set_parts_str(self,partstr):

        self.partflg = None
        self.partstr = partstr

        if self.partstr == None : return

        token        = self.partstr.split(',')
        self.partflg = token[0]

        self.chunksize     = int(token[1])
        self.block_count   = 1
        self.remainder     = 0
        self.current_block = 0
        self.lastchunk     = True

        self.offset        = 0
        self.length        = self.chunksize

        self.filesize      = self.chunksize

        if self.partflg == '1' : return

        self.block_count   = int(token[2])
        self.remainder     = int(token[3])
        self.current_block = int(token[4])
        self.lastchunk     = self.current_block == self.block_count-1

        self.offset        = self.current_block * self.chunksize

        self.filesize      = self.block_count * self.chunksize

        if self.remainder  > 0 :
           self.filesize  += self.remainder   - self.chunksize
           if self.lastchunk : self.length    = self.remainder

    def set_rename(self,rename=None):
        if rename != None :
           self.headers['rename'] = rename
        elif 'rename' in self.headers :
           del self.headers['rename']

    def set_source(self,source=None):
        if source != None :
           self.headers['source'] = source
        elif 'source' in self.headers :
           del self.headers['source']

    def set_sum(self,sumflg='d',checksum=0):
        self.sumflg    =  sumflg
        self.checksum  =  checksum
        self.sumstr    =  None
        if self.sumflg == None : return
        self.sumstr    = '%s,%s' % (sumflg,checksum)

    def set_sum_str(self,sumstr):
        self.sumflg  = None
        self.sumstr  = sumstr
        if sumstr == None : return

        token        = self.sumstr.split(',')
        self.sumflg  = token[0]
        self.checksum= token[1]

        # file was removed
        if self.sumflg == 'R' : return

        self.chkclass.from_list(self.sumflg)
        self.compute_chksum = self.chkclass.checksum

    def set_suffix(self):
        if self.partstr == None : return
        if self.sumstr  == None or self.sumflg == 'R' : return
        self.suffix = self.part_suffix()

    def set_time(self):
        msec = '.%d' % (int(round(time.time() * 1000)) %1000)
        now  = time.strftime("%Y%m%d%H%M%S",time.gmtime()) + msec
        self.time = now

    def set_to_clusters(self,to_clusters=None):
        if to_clusters != None :
           self.headers['to_clusters'] = to_clusters
           self.to_clusters = to_clusters.split(',')
        elif 'to_clusters' in self.headers :
           del self.headers['to_clusters']
           self.to_clusters = []

    def set_topic_url(self,topic_prefix,url):
        self.topic_prefix = topic_prefix
        self.url          = url
        path              = url.path.strip('/')
        self.subtopic     = path.replace('/','.')
        self.topic        = '%s.%s' % (topic_prefix,self.subtopic)
        self.topic        = self.topic.replace('..','.')

    def set_topic_usr(self,topic_prefix,subtopic):
        self.topic_prefix = topic_prefix
        self.subtopic     = subtopic
        self.topic        = '%s.%s' % (topic_prefix,self.subtopic)
        self.topic        = self.topic.replace('..','.')

    def start_timer(self):
        self.tbegin = time.time()

    def verify_part_suffix(self,filepath):
        filename = os.path.basename(filepath)
        token    = filename.split('.')

        try :  
                 self.suffix = '.' + '.'.join(token[-6:])
                 if token[-1] != self.part_ext : return False,'not right extension'

                 self.chunksize     = int(token[-6])
                 self.block_count   = int(token[-5])
                 self.remainder     = int(token[-4])
                 self.current_block = int(token[-3])
                 self.sumflg        = token[-2]

                 if self.current_block >= self.block_count : return False,'current block wrong'
                 if self.remainder     >= self.chunksize   : return False,'remainder too big'

                 self.length    = self.chunksize
                 self.lastchunk = self.current_block == self.block_count-1
                 self.filesize  = self.block_count * self.chunksize
                 if self.remainder  > 0 :
                    self.filesize  += self.remainder - self.chunksize
                    if self.lastchunk : self.length  = self.remainder

                 lstat     = os.stat(filepath)
                 fsiz      = lstat[stat.ST_SIZE] 

                 if fsiz  != self.length : return False,'wrong file size'

                 self.chkclass.from_list(self.sumflg)
                 self.compute_chksum = self.chkclass.checksum

                 self.checksum  = self.compute_chksum(filepath,0,fsiz)

        except :
                 (stype, svalue, tb) = sys.exc_info()
                 self.logger.error("Type: %s, Value: %s" % (stype, svalue))
                 return False,'incorrect extension'

        return True,'ok'
