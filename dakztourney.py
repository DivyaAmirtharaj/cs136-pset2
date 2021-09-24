#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class DakzTourney(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        requests = []

        # Sorted list of the rarest pieces and the peers that have them
        piece_dict = {}
        for peer in peers:
            av_set = set(peer.available_pieces)
            for piece in av_set:
                piece_dict.setdefault(piece, [])
                piece_dict[piece].append(peer.id)
        avail_set = set(piece_dict.keys())
        # Rarest order is a list of tuples with the rarest pieces first
        # and the peers that have the corresponding piece
        rarest_order = []
        for k in sorted(piece_dict, key=lambda k: len(piece_dict[k]), reverse=False):
            rarest_order.append((k, piece_dict[k]))
        
        isect = np_set.intersection(avail_set)
        # in order of piece rarity, request the piece from all players that have it
        for item in rarest_order:
            if item[0] in isect:
                start_block = self.pieces[item[0]]
                while len(item[1]) != 0:
                    req_peer = random.choice(item[1])
                    r = Request(self.id, req_peer, item[0], start_block)
                    item[1].remove(req_peer)
                    requests.append(r)
        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        requester_id_list = []
        uploads = []
        #self.dummy_state["unchoke"] = ""

        for request in requests:
            requester_id_list.append(request.requester_id)
        random.shuffle(requester_id_list)

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")

        else:
            if 1 <= len(requests) <= 3:
                bw_short = even_split(self.up_bw, len(requests))
                for i, request in enumerate(requests):
                    uploads.append(Upload(self.id, request.requester_id, bw_short[i]))
            else:
                down_dict = {}
                for hist1 in history.downloads[round-1]:
                    if hist1.from_id in down_dict:
                        down_dict[hist1.from_id] += hist1.blocks
                    else: 
                        down_dict[hist1.from_id] = hist1.blocks
                for hist2 in history.downloads[round-2]:
                    if hist2.from_id in down_dict:
                        down_dict[hist2.from_id] += hist2.blocks
                    else: 
                        down_dict[hist2.from_id] = hist2.blocks
                sorted_down_dict = dict(sorted(down_dict.items(), key=lambda item: item[1], reverse=True))
                
                bws = even_split(self.up_bw, 4)
                uploaded = 0
                for requester in sorted_down_dict:
                    if requester in requester_id_list:
                        uploads.append(Upload(self.id, requester, bws[uploaded]))
                        requester_id_list.remove(requester)
                        uploaded += 1
                    if uploaded == 3:
                        break
                while uploaded < 3:
                    rand_req = random.choice(requester_id_list)
                    uploads.append(Upload(self.id, rand_req, bws[uploaded]))
                    requester_id_list.remove(rand_req)
                    uploaded += 1
                
                if round % 1 == 0 and round != 0:
                    if len(requester_id_list) != 0:
                        opt_unchoke = random.choice(requester_id_list)
                        self.dummy_state["unchoke"] = opt_unchoke
                if round >= 1 and ("unchoke" in self.dummy_state) and (self.dummy_state["unchoke"] in requester_id_list):
                    uploads.append(Upload(self.id, self.dummy_state["unchoke"], bws[3]))                        
                
        return uploads
