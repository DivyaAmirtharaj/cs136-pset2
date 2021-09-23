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
                    print("newly random!", r)
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

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            request = random.choice(requests)
            chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
