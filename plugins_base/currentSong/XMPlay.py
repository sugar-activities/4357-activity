# -*- coding: utf-8 -*-

#   This file is part of emesene.
#
#    Emesene is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    emesene is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with emesene; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import os
import gobject
import gettext

ERROR = ''

try:
    import win32api
    import win32gui
    import locale
except:
    ERROR = 'cannot import needed modules'


import CurrentSong

class XMPlay( CurrentSong.CurrentSong ):

    def __init__( self ):
        CurrentSong.CurrentSong.__init__( self )
        self.xmplay = None
        self.isRunning()
        self.currentSong = ''
        
    def isPlaying( self ):
        if self.xmplay and win32api.SendMessage(self.xmplay, 0x400, 0, 104) == 0:
            return False
         
        return True
        
    def isRunning( self ):
        try:
            self.xmplay = win32gui.FindWindow('XMPLAY-MAIN', None)
            return True
        except: 
            return False

    def getCurrentSong( self ):
        return self.currentSong

    def check( self ):
        if not self.isRunning(): return False
        
        if self.isPlaying():
            string = 'XMPlay\\0Music\\01\\0{0}\\0%s\\0\\0' % \
                win32gui.GetWindowText (self.xmplay)
            enc = locale.getpreferredencoding ()
            if enc == '':
                enc = 'windows-1252'
            newCurrentSong = unicode (string, enc)
            print newCurrentSong
        else:
            newCurrentSong = ''

        if self.currentSong != newCurrentSong:
            self.currentSong = newCurrentSong
            return True
            
        return False
    
    def getStatus( self ):
        '''
        check if everything is OK to start the plugin
        return a tuple whith a boolean and a message
        if OK -> ( True , 'some message' )
        else -> ( False , 'error message' )
        '''
        
        if os.name != 'nt':
            return ( False, 'This plugin only works on windows systems' )
        
        if ERROR != '':
            return ( False, ERROR )
        
        return ( True, 'Ok' )
