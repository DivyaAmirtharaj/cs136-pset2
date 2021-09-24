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

class DakzTyrant(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dij = dict()
        self.uij = dict()
        self.rates = dict()
        self.unchoked_me = dict()
    
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

        uploads = []
        request_ids = [r.requester_id for r in requests]

        if round == 0:
            for j in peers:
                self.uij[j.id] = self.up_bw / 4
                self.dij[j.id] = len(j.available_pieces) / 4
                self.unchoked_me[j.id] = 0
        i_unchoked = []
        upload_bws = []

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            gamma = 0.1
            r = 3
            alpha = 0.2
            
            for j in peers:
                self.rates[j.id] = self.dij[j.id] / self.uij[j.id]
            
            cap = self.up_bw

            while cap > 0 and len(self.rates) > 0:
                max_rate = max(list(self.rates.values()))
                max_ids = []
                for id in self.rates:
                    if self.rates[id] == max_rate:
                        max_ids.append(id)
                to_upload = random.choice(max_ids)
                
                if cap - self.uij[to_upload] > 0 and to_upload in request_ids:
                    i_unchoked.append(to_upload)
                    upload_bws.append(self.uij[to_upload])
                    cap -= self.uij[to_upload]

                self.rates.pop(to_upload)

            if round != 0:
                prev_down_history = history.downloads[round - 1]
                download_blocks = {}

                # finding the number of blocks i (self) downloaded from j
                for d in prev_down_history:
                    if d.to_id == self.id:
                        j_id = d.from_id
                        if j_id not in download_blocks:
                            download_blocks[j_id] = d.blocks
                        else:
                            download_blocks[j_id] += d.blocks
        
                # counting which peers unchoked me in the last round
                for j in peers:
                    if j.id in download_blocks:
                        self.unchoked_me[j.id] += 1
                    else:
                        self.unchoked_me[j.id] = 0
            
            # only update the peers that i unchoked this past round
            for j in i_unchoked:
                if round > 0:
                    # if the peer didn't unchoke me, i need to increase my bandwidth
                    if self.unchoked_me[j] == 0:
                        self.uij[j] = self.uij[j] * (1 + alpha)

                        # update download speed according to section 5.4.3
                        for p in peers:
                            if p.id == j:
                                self.dij[j] = len(p.available_pieces) / 4
                    else:
                        # if the peer did unchoke me, then i can use the download speed
                        # from this past round
                        self.dij[j] = download_blocks[j]

                        # if it unchoked me for more than 3 rounds, decrease the bandwidth
                        if self.unchoked_me[j] >= r:
                            self.uij[j] = self.uij[j] * (1 - gamma)

        # use the bandwidths calculated above
        for i in range(len(i_unchoked)):
            uploads.append(Upload(self.id, i_unchoked[i], upload_bws[i]))
            
        return uploads
