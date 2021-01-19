from PyQt5.QtGui import *
import PyQt5.QtWidgets
from electroncash.plugins import BasePlugin, hook

from electroncash_gui.qt.util import *

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from electroncash.transaction import Transaction
from electroncash.slp import SlpMessage, SlpUnsupportedSlpTokenType, SlpInvalidOutputMessage

import tempfile
import os
import random
import webbrowser
import urllib
import json
import random

class Plugin(BasePlugin, QObject):
    got_network_response_sig = pyqtSignal()

    @pyqtSlot()
    def got_network_response_slot(self):
        self.download_finished = True

        resp = self.json_response
        if resp.get('error'):
            return self.fail_genesis_info("Download error!\n%r"%(resp['error'].get('message')))
        raw = resp.get('result')

        tx = Transaction(raw)
        self.handle_genesis_tx(tx)

    @hook
    def on_new_window(self, window):
        self.init_qt(window.gui_object)

    @hook
    def init_qt(self, gui):
        if (not len(gui.windows)):
            return
        self.window = gui.windows[0]
        self.network = self.window.network
        self.wallet = self.window.wallet

        token_types = self.wallet.token_types.copy()
        grp = "a2987562a405648a6c5622ed6c205fca6169faa8afeb96a994b48010bd186a66"

        self.tokens = []
        self.tokenIds = []
        for k, v in token_types.items():
            if v['class'] != 'SLP65':
                continue

            if v['group_id'] == grp:
                self.tokenIds.append(k)

        self.listWidget = QListWidget()
        self.listWidget.setViewMode(QListWidget.IconMode)
        self.listWidget.setResizeMode(QListWidget.Adjust)
        self.listWidget.setIconSize(QSize(256,256))

        file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ayaya.png")
        icon = QIcon(file)
        self.listWidget.tab_icon = icon

        self.window.tabs.addTab(self.listWidget, icon, "&Waifu".replace("&", ""))
        self.listWidget.itemDoubleClicked.connect(self.handleDoubleClick)

        for tokenId in self.tokenIds:
            self.download_info(tokenId)

    def handleDoubleClick(item):
        text = item.text()
        token = [token for token in self.tokens if token['token_name'] == text][0]
        if random.randint(0,100) == 0:
            webbrowser.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', new=2)
        else:
            webbrowser.open(f"https://simpleledger.info/#token/{token}", new=2)

    def download_info(self, txid):
        try:
            tx = self.wallet.transactions[txid]
        except KeyError:
            def callback(response):
                self.json_response = response

                self.got_network_response_sig.emit()

            requests = [ ('blockchain.transaction.get', [txid]), ]
            self.network.send(requests, callback)
        else:
            self.handle_genesis_tx(tx)

    def handle_genesis_tx(self, tx):
        txid = tx.txid()

        try:
            slpMsg = SlpMessage.parseSlpOutputScript(tx.outputs()[0][1])
        except SlpUnsupportedSlpTokenType as e:
            return self.fail_genesis_info(_("Unsupported SLP token version/type - %r.")%(e.args[0],))
        except SlpInvalidOutputMessage as e:
            return self.fail_genesis_info(_("This transaction does not contain a valid SLP message.\nReason: %r.")%(e.args,))
        if slpMsg.transaction_type != 'GENESIS':
            return self.fail_genesis_info(_("This is an SLP transaction, however it is not a genesis transaction."))

        slpMsg.op_return_fields['token_id'] = txid
        self.tokens.append(slpMsg.op_return_fields)

        dir = os.path.join(tempfile.gettempdir(), 'waifu')
        try:
            os.makedirs(dir)
        except:
            pass
        file = os.path.join(dir, f"{txid}.png")
        url = f"https://icons.waifufaucet.com/original/{txid}.png"
        if not os.path.isfile(file):
            urllib.request.urlretrieve(url, file)
        name = slpMsg.op_return_fields['token_name'].decode("utf-8")
        item = QListWidgetItem(QIcon(file), name)
        self.listWidget.addItem(item)
