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

VERSION = '0.4'

import Plugin
import gettext
import gtk
import Conversation
import encryptMessage

class MainClass( Plugin.Plugin ):
    '''Main plugin class'''
    
    description = _('Plugin to encode/decode your messages')
    authors = { 'Matheus Bratfisch' : 'matheusbrat@gmail.com' }
    website = 'http://www.matbra.com'
    displayName = _('Encode Plugin')
    name = 'EncryptedMessage'
    
    def __init__( self, controller, msn ):
        '''Contructor'''
        Plugin.Plugin.__init__( self, controller, msn )
        self.enabled = False;
        self.description = _('Plugin to encode/decode your messages')
        self.authors = { 'Matheus Bratfisch' : 'matheusbrat@gmail.com' }
        self.website = 'http://www.matbra.com'
        self.displayName = _('Encode Plugin')
        self.name = 'EncryptedMessage'
        self.controller = controller
        self.config = controller.config
        self.config.readPluginConfig(self.name)
        self.Slash = controller.Slash
        
    def start( self ):
        '''start the plugin'''
        conv_manager = self.controller.conversationManager
        self.receiveId = conv_manager.connect('receive-message', self.decode)
        self.insertId = conv_manager.connect('new-conversation-ui', self.insertButton)
        
        self.Slash.register('we', self.withoutEncode, _('Send your messages without encode.'))
        self.Slash.register('password', self.changePassword, _('Change your password'))
        self.Slash.register('undefault', self.unsetDefault, _('Unset the default option for this conversation'))
        
        self.enabled = True
        
        self.lockImage = self.getLockImage()
        self.unlockImage = self.getUnlockImage()

        for window, conversation in self.controller.conversationManager.conversations:
            self.insertButton(conv_manager, conversation, window)

    def stop( self ):    
        '''stop the plugin'''
        conv_manager = self.controller.conversationManager
        
        self.Slash.unregister('we')
        self.Slash.unregister('password')
        
        conv_manager.disconnect(self.receiveId)
        conv_manager.disconnect(self.insertId)
        
        for window, conversation in self.controller.conversationManager.conversations:
            toolbar = conversation.ui.input.toolbar
            conversation.enabledEncrypt = False
            try: 
                toolbar.remove(toolbar.setEncryptButton)
            except:
                pass
        
        self.enabled = False
        
    def getEncodeList(self):
        ''' get types of available encode'''
        return [ x for x in dir( encryptMessage ) \
                 if not x.startswith( "__" ) \
                 and x != 'MainEncryptedMessage' ]
        
    def windowConfigure(self):
        ''' show a window to choose encryptation'''
        l = []
        l.append(Plugin.Option('encodeType', list, _('Encode:'), \
                               _('Select the Encryption  of this conversation'), 'rijndael', \
                               self.getEncodeList()))
        l.append(Plugin.Option('defaultType', bool, _('Default type for this conversation:'), \
                               _('Is this option default?'), False))
        self.configWindow = Plugin.ConfigWindow( _( 'Config Plugin' ), l )
        response = self.configWindow.run()
        return response   
        
    def check( self ):
        '''Check Plugin'''
        return ( True, 'Ok' )   
     
    def withoutEncode(self, slash_action):
        ''' send the message without encode when used /we '''
        message = slash_action.getParams()
        conversation = slash_action.getConversation()
        
        conversation.enabledEncrypt = False
        slash_action.outputText(message, True)
        conversation.enabledEncrypt = True
        
    def unsetDefault(self, slash_action):
        ''' unset the default option for this conversation '''
        conversation = slash_action.getConversation()
        conversation.defaultOption = False
            
    def changePassword(self, slash_action):
        ''' ask to encodeDecode to change password '''
        conversation = slash_action.getConversation()
        
        if conversation.enabledEncrypt:
            conversation.encoderDecoder.changePassword()
            
            
    def insertButton(self, cm, conversation, window):
        ''' insert the toolbar button '''
        if self.enabled is True:
            # encrypt icon               
            toolbar = conversation.ui.input.toolbar
            toolbar.encrycon = gtk.Image()
            toolbar.encrycon.set_from_pixbuf(self.unlockImage)
                
            toolbar.setEncryptButton = gtk.ToolButton(toolbar.encrycon, _('Configure encrypt'))
            toolbar.setEncryptButton.connect('clicked', self.sendEncryptClicked, conversation)
            toolbar.insert(toolbar.setEncryptButton, -1)
            toolbar.setEncryptButton.set_tooltip_text(_('Enable Encode'))
               
            toolbar.show_all()
                
        
    def sendEncryptClicked(self, *args):
        ''' action when encrypt button is pressed '''
        conversation = args[1]
        toolbar = conversation.ui.input.toolbar
        
        def do_receive_message(mail, nick, message, format, charset, p4c):
            ''' this method replace the Conversation one when encode is enabled '''
            if conversation.config.user['autoReply'] and not conversation.autoreplySent:
                msg = conversation.config.user['autoReplyMessage']
    
                # no gettext here, it's a semi standard way
                # to identify automessages
                conversation.switchboard.sendMessage(_('AutoMessage: ') + msg)
                conversation.appendOutputText(None, _('AutoMessage: %s\n') % msg, \
                    'information')
                conversation.autoreplySent = True
            if message is None:
                return
                
            try:
                encrypt = conversation.controller.pluginManager.getPlugin("EncryptedMessage")
                isEc = conversation.encoderDecoder.isEncrypted(message)
            except:
                isEc = encrypt = None
                
            if not (conversation.controller.pluginManager.isEnabled("EncryptedMessage") and isEc and conversation.enabledEncrypt):
                if p4c: # give p4context name instead of mail
                    conversation.appendOutputText(nick, message, 'incoming', p4c, \
                        conversation.parseFormat(mail, format))
                else:
                    conversation.appendOutputText(mail, message, 'incoming', p4c, \
                        conversation.parseFormat(mail, format))
                           
            conversation.doMessageWaiting(mail)
        
        def do_send_message(message, retry=0):
            ''' this method replace the Conversation one when encode is enabled '''
            
            remoteMail = conversation.switchboard.firstUser
            remoteStatus = conversation.controller.contacts.get_status(remoteMail)
            
            encrypt = conversation.controller.pluginManager.getPlugin("EncryptedMessage")
            if conversation.controller.pluginManager.isEnabled("EncryptedMessage") and conversation.enabledEncrypt:
                messageEncode = encrypt.encode(conversation, message)
                messageChunks = Conversation.splitMessage(messageEncode)
                message = message + _(' (send encoded) ')
            else:
                messageChunks = Conversation.splitMessage(message)
            
            
            def do_send_offline(response, mail='', message=''):
                '''callback for the confirm dialog asking to send offline
                message'''
                conversation.sendOffline = True
                conversation.switchboard.msn.msnOIM.send(mail, message)
                conversation.appendOutputText(self.user, message, 'outgoing')
    
            if conversation.switchboard.status == 'error' and remoteStatus == 'FLN':
                do_send_offline(stock.YES, remoteMail, message)
                return
    
            if conversation.switchboard.status == 'closed':
                conversation.reconnect()
    
            alreadyShow = False
            
            for chunk in messageChunks:
                try:
                    # why is conversation sending custom emoticons manually?
                    conversation.switchboard.sendCustomEmoticons(chunk)
                    conversation.switchboard.sendMessage(chunk, conversation.getStyle(chunk))
                    if alreadyShow is False:
                        conversation.appendOutputText(conversation.user, message, 'outgoing')
                        alreadySend = True
                        
                except Exception, e:
                    raise
                    print str(e)
                    conversation.reconnect()
                    if retry < 3:
                        conversation.do_send_message(
                            ''.join(messageChunks[messageChunks.index(chunk):]), \
                            retry + 1)
                    else:
                        conversation.appendOutputText(None, _('Can\'t send message'), \
                            'information')
                    return        
        
        def changeDO():
            ''' this method change between enable and disable keeping the method correct '''
            try: 
                if conversation.do_receive_message_old and conversation.do_send_message_old:
                    tempReceive = conversation.do_receive_message 
                    tempSend = conversation.do_send_message
                    
                    conversation.do_receive_message = conversation.do_receive_message_old
                    conversation.do_send_message = conversation.do_send_message_old
                    
                    conversation.do_receive_message_old = tempReceive
                    conversation.do_send_message_old = tempSend
            except:
                conversation.do_receive_message_old = conversation.do_receive_message
                conversation.do_send_message_old = conversation.do_send_message
                
                conversation.do_receive_message = do_receive_message
                conversation.do_send_message = do_send_message
                
        def changeButtonAndLabes(enabled, image, tooltipText):
            ''' change Image Button, Labels ... '''
            changeDO()
            conversation.enabledEncrypt = enabled
            toolbar.encrycon.set_from_pixbuf(image)
            toolbar.setEncryptButton.set_tooltip_text(tooltipText)
                   
        def analysisResult(result):
            if result is not None:
                try:
                    conversation.encoderDecoder = getattr(encryptMessage, result['encodeType'].value)(self)
                    conversation.defaultOption  = result['defaultType'].value
                except Exception, e:
                    print _("Error initializing encrypted message")
                    print e
                    error = e
                
                changeButtonAndLabes(True,self.getLockImage(), _('Disable Encode'))
                
        if self.controller.pluginManager.isEnabled("EncryptedMessage") is True:
            if conversation.enabledEncrypt is False:
                    if conversation.encoderDecoder is None or conversation.defaultOption is False:
                        result = self.windowConfigure()
                        analysisResult(result)
                    else:
                        changeButtonAndLabes(True,self.getLockImage(), _('Disable Encode'))
            else:
                changeButtonAndLabes(False, self.getUnlockImage(), _('Enable Encode')) 
            
        
    def decode(self, cm, conversation, mail, nick, message, format, charset, p4c):
        ''' decode the message '''
        try:
            isEc = conversation.encoderDecoder.isEncrypted(message)
            isEn = conversation.enabledEncrypt
        except: 
            isEc = False 
            isEn = False
                 
        if not isEc or self.enabled is False or isEn is False:
            return
        
        texto = conversation.encoderDecoder.decode(conversation, message)
        conversation.do_receive_message(mail, nick, texto, format, charset, p4c)
        

    def encode(self, conversation, message):
        ''' encode the message '''
        encodedMessage = conversation.encoderDecoder.encode(conversation, message)
        return encodedMessage
     
    """ About the images below: 
    
    "Dropline Etiquette is released under the terms of both GNU General Public License
    and CC Attribution-Share Alike 3.0."

    http://www.silvestre.com.ar/?p=3""" 
     
    def getLockImage(self):
        ''' return the image with the green Locker'''
        lock = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17\x0c\x0c\x0c\x84SSS\xd9lll\xeaaaa\xdf"""\x9d\x00\x00\x00\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00_hhh\xfa\xc7\xc7\xc7\xff\xd5\xd5\xd5\xff\xd2\xd2\xd2\xff\xce\xce\xce\xff\xbc\xbc\xbc\xfflll\xfd\x13\x13\x13\x87\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Tzzz\xfe\xd6\xd6\xd6\xff\xd2\xd2\xd2\xff\xbe\xbe\xbe\xff\x96\x96\x96\xff\xac\xac\xac\xff\xd2\xd2\xd2\xff\xcb\xcb\xcb\xff|||\xff\x0b\x0b\x0b\x87\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07***\xee\xcf\xcf\xcf\xff\xd2\xd2\xd2\xffuuu\xff\x05\x05\x05\xf5\x00\x00\x00\xd9\x00\x00\x00\xeeGGG\xff\xcf\xcf\xcf\xff\xc0\xc0\xc0\xffQQQ\xf9\x00\x00\x00)\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Jvvv\xff\xd3\xd3\xd3\xff\x9d\x9d\x9d\xff\x02\x02\x02\xe7\x00\x00\x00V\x00\x00\x00\x07\x00\x00\x00\n\x00\x00\x00\xc1\x89\x89\x89\xff\xd2\xd2\xd2\xff\x80\x80\x80\xff\x00\x00\x00\x88\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00c\x94\x94\x94\xff\xd2\xd2\xd2\xfflll\xff\x00\x00\x00\xaf\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00?eee\xff\xd2\xd2\xd2\xff\x93\x93\x93\xff\x00\x00\x00\xaf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Z\xa4\xa4\xa4\xff\xd2\xd2\xd2\xffccc\xff\x00\x00\x00\x9e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00-```\xff\xd2\xd2\xd2\xff\x97\x97\x97\xff\x00\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00=B>\x19\xd3\xc1\xbc\x97\xff\xe0\xda\xb6\xff\x96\x8fl\xffWP,\xf3\\T/\xe5\\T/\xe5\\R/\xe5XN,\xe9\x8e\x83d\xff\xdc\xcf\xb1\xff\xae\xa1\x82\xff+\x1f\x04\xec\x00\x00\x00]\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17g`\x11\xfa\xfe\xf1x\xff\xfd\xe6:\xff\xfb\xe0-\xff\xfa\xd9%\xff\xf8\xd3\x1d\xff\xf7\xcc\x15\xff\xf5\xc5\r\xff\xf3\xbe\x06\xff\xf1\xb7\x00\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xffdB\x00\xfc\x00\x00\x00;\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x95\x8b\x1e\xff\xfe\xecN\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xed\xc0\x00\xff\xd0\xa5\x00\xff\xe9\xb4\x00\xff\xf1\xb7\x00\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x96d\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xea=\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xffs^\x04\xff\x11\x0f\x07\xff\x1b\x17\x0b\xff\xce\xa0\x13\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x8f_\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe9/\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff<2\n\xff\x00\x00\x00\xff\x00\x00\x00\xff}i)\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x86Y\x00\xff\x00\x00\x00q\x00\x00\x00O\x07\x19\x07q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe7 \xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xae\x8f\t\xff\r\x0b\x06\xff!\x1d\x11\xff\xdd\xb0"\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xffyP\x00\xff\n!\n\xcf)\xa2)\xfb\n>\n\xc6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe6\x11\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xd9\xaf\x00\xff\x0b\t\x04\xff\x18\x14\x0b\xff\xe8\xb1\x01\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xaew\x00\xff&b\x17\xff3\xcc3\xff\x0cJ\x0c\xda\x00\x00\x00\x17\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1d\xff\xfd\xe4\x03\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff}i\x15\xff\x00\x00\x00\xff2{2\xff9X\x1a\xff\xe7\xaa\x00\xff\xe9\xa8\x00\xffdW\x06\xff.\xa3)\xff3\xd93\xff\x0cL\x0c\xee\x00\x00\x00\x1d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x8f\x85\x12\xff\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xce\xaa\x13\xff\xbb\x9a\x1d\xffFS\x16\xffQ\xd9Q\xff9V\x0f\xff8e\x14\xff5\xd05\xff/\xd5/\xff\x16U\x0b\xff\x00\x00\x00\x85\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00J\x88~\x03\xff\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xf6\xc7\x00\xff\xf4\xc2\x00\xff\xc4\x98\x00\xff4\xa81\xff=\xdd=\xff6\xdf6\xff+\xd2+\xff\x1fe\x0c\xffK2\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 d\\\x00\xfe\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xf6\xc7\x00\xff\xf4\xc2\x00\xff\xf3\xbc\x00\xffC^\x0c\xff2\xdc2\xff(\xce(\xff\x1bj\x0c\xff\x8ea\x00\xffC+\x00\xfd\x00\x00\x00\\\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x0e\x00\x00\x00\x18\x00\x00\x00w?8\x00\xe7SI\x00\xf3PE\x00\xf3LA\x00\xf4I<\x00\xf6E8\x00\xf6B5\x00\xf6?2\x00\xf7) \x00\xfa\x1b\xa0\x1a\xff\x0fl\x0b\xfe*\x1e\x00\xf8+\x1e\x00\xf1\x01\x01\x00\xad\x00\x00\x003\x00\x00\x00\x1a\x00\x00\x00\x10\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\t\x00\x00\x00\x11\x00\x00\x00!\x00\x00\x00(\x00\x00\x00.\x00\x00\x002\x00\x00\x004\x00\x00\x006\x00\x00\x006\x00\x00\x004\x01\x19\x01\xae\x00\x00\x00k\x00\x00\x00)\x00\x00\x00"\x00\x00\x00\x13\x00\x00\x00\x0b\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        lock = lock
        lockPixBuf = gtk.gdk.pixbuf_new_from_data(lock, gtk.gdk.COLORSPACE_RGB, True, 8, 22, 22, 88)
        return lockPixBuf
    
    def getUnlockImage(self):
        ''' return the image with the red locker'''
        unlock = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17\x0c\x0c\x0c\x84SSS\xd9lll\xeaaaa\xdf"""\x9d\x00\x00\x00\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00_hhh\xfa\xc7\xc7\xc7\xff\xd5\xd5\xd5\xff\xd2\xd2\xd2\xff\xce\xce\xce\xff\xbc\xbc\xbc\xfflll\xfd\x13\x13\x13\x87\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Tzzz\xfe\xd6\xd6\xd6\xff\xd2\xd2\xd2\xff\xbe\xbe\xbe\xff\x96\x96\x96\xff\xac\xac\xac\xff\xd2\xd2\xd2\xff\xcb\xcb\xcb\xff|||\xff\x0b\x0b\x0b\x87\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07***\xee\xcf\xcf\xcf\xff\xd2\xd2\xd2\xffuuu\xff\x05\x05\x05\xf5\x00\x00\x00\xd9\x00\x00\x00\xeeGGG\xff\xcf\xcf\xcf\xff\xc0\xc0\xc0\xffQQQ\xf9\x00\x00\x00)\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Jvvv\xff\xd3\xd3\xd3\xff\x9d\x9d\x9d\xff\x02\x02\x02\xe7\x00\x00\x00V\x00\x00\x00\x07\x00\x00\x00\n\x00\x00\x00\xc1\x89\x89\x89\xff\xd2\xd2\xd2\xff\x80\x80\x80\xff\x00\x00\x00\x88\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00c\x94\x94\x94\xff\xd2\xd2\xd2\xfflll\xff\x00\x00\x00\xaf\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00?eee\xff\xd2\xd2\xd2\xff\x93\x93\x93\xff\x00\x00\x00\xaf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Z\xa4\xa4\xa4\xff\xd2\xd2\xd2\xffccc\xff\x00\x00\x00\x9e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00-```\xff\xd2\xd2\xd2\xff\x97\x97\x97\xff\x00\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00=B>\x19\xd3\xc1\xbc\x97\xff\xe0\xda\xb6\xff\x96\x8fl\xffWP,\xf3\\T/\xe5\\T/\xe5\\R/\xe5XN,\xe9\x8e\x83d\xff\xdc\xcf\xb1\xff\xae\xa1\x82\xff+\x1f\x04\xec\x00\x00\x00]\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17g`\x11\xfa\xfe\xf1x\xff\xfd\xe6:\xff\xfb\xe0-\xff\xfa\xd9%\xff\xf8\xd3\x1d\xff\xf7\xcc\x15\xff\xf5\xc5\r\xff\xf3\xbe\x06\xff\xf1\xb7\x00\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xffdB\x00\xfc\x00\x00\x00;\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00H\x95\x8b\x1e\xff\xfe\xecN\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xed\xc0\x00\xff\xd0\xa5\x00\xff\xe9\xb4\x00\xff\xf1\xb7\x00\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x96d\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xea=\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xffs^\x04\xff\x11\x0f\x07\xff\x1b\x17\x0b\xff\xce\xa0\x13\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x8f_\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe9/\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff<2\n\xff\x00\x00\x00\xff\x00\x00\x00\xff}i)\xff\xf0\xb1\x00\xff\xee\xab\x00\xff\xed\xa6\x00\xff\xeb\xa0\x00\xff\x86Y\x00\xff\x00\x00\x00q\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe7 \xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xae\x8f\t\xff\r\x0b\x06\xff!\x1d\x11\xff\xdd\xb0"\xff\xf0\xb1\x00\xff\xe8\xa7\x00\xff\xca\x8d\x00\xff\xeb\xa0\x00\xff}S\x00\xff\x00\x00\x00t\x00\x00\x00&\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1e\xff\xfd\xe6\x11\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xd9\xaf\x00\xff\x0b\t\x04\xff#\x1e\x0f\xff\xf1\xb7\x01\xff\xec\xae\x00\xffyC*\xff\xd0zx\xff\x81T\x05\xffoJ\x00\xffX!!\xeb\xbcFF\xfb\x12\x04\x04r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x95\x8b\x1d\xff\xfd\xe4\x03\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff}i\x15\xff\x00\x00\x00\xff\x00\x00\x00\xff\xbe\x97\x1c\xff\xd9\xa0\x00\xff\xba`]\xff\xfe\x95\x95\xff\xd3^]\xffa"\x1c\xff\xf4VV\xff\xf4EE\xff<\x0b\x0b\xcf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00K\x8f\x85\x12\xff\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xce\xaa\x13\xff\xbb\x9a\x1d\xff\xc4\xa0&\xff\xdd\xae\x1b\xff\xf0\xb1\x00\xff\x96k\x01\xff\xb9GD\xff\xf8YY\xff\xf7FF\xff\xee00\xffJ\x08\x08\xe4\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00J\x88~\x03\xff\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xf6\xc7\x00\xff\xf4\xc2\x00\xff\xf3\xbc\x00\xff\xf1\xb7\x00\xff\xf0\xb1\x00\xff\xe5\xa4\x00\xffb$\x10\xff\xed//\xff\xee\x1c\x1c\xff\xbb\x07\x07\xfe\r\x00\x00\x8a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 d\\\x00\xfe\xfd\xe4\x00\xff\xfc\xde\x00\xff\xfa\xd9\x00\xff\xf9\xd3\x00\xff\xf7\xcd\x00\xff\xf6\xc7\x00\xff\xf4\xc2\x00\xff\xf3\xbc\x00\xff\xf1\xb7\x00\xff\xeb\xad\x00\xffc#\n\xff\xdd\x19\x19\xff\xdd\x07\x07\xff\xa4\x00\x00\xff\xe4\x00\x00\xff\xab\x00\x00\xfc\x0e\x00\x00|\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x0e\x00\x00\x00\x18\x00\x00\x00w?8\x00\xe7SI\x00\xf3PE\x00\xf3LA\x00\xf4I<\x00\xf6E8\x00\xf6B5\x00\xf6?2\x00\xf7<-\x00\xf74&\x00\xf8\x81\x04\x03\xff\xd5\x00\x00\xffA\x03\x00\xfd\x04\x01\x00\xd1\x92\x00\x00\xfa\xd2\x00\x00\xff2\x00\x00\xd0\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\t\x00\x00\x00\x11\x00\x00\x00!\x00\x00\x00(\x00\x00\x00.\x00\x00\x002\x00\x00\x004\x00\x00\x006\x00\x00\x006\x00\x00\x004\x00\x00\x002\x02\x00\x00t\'\x00\x00\xd2\x00\x00\x002\x00\x00\x00\x13\x05\x00\x00d*\x00\x00\xc9\x00\x00\x00\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        lockPixBuf = gtk.gdk.pixbuf_new_from_data(unlock, gtk.gdk.COLORSPACE_RGB, True, 8, 22, 22, 88)
        return lockPixBuf