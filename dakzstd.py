#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

#Reference client (5.3.1) - rarest-first, reciprocation, and optimistic unchoking
# peers.sort - rarest first

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class DakzStd(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
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

        # To-do:
        # 1. Sort the pieces by rarity, identify which peers have which pieces
        # 2. For the first round, randomly choose a Seed Peer to get the rarest piece from
        # 3. After the first round, request the rarest piece from the peer with the fastest upload

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
        for k in sorted(piece_dict, key=lambda k: len(piece_dict[k]), reverse=True):
            rarest_order.append((k, piece_dict[k]))
        print(rarest_order)

        
        ''' for peer in peers:
            print("peer", peer)
            # Set of the intersection of pieces required, and the pieces peers have available
            isect = np_set.intersection(avail_set)
            
            # If the current round is 0, choose the rarest piece (if it is in isect)
            # then randomly choose a seed to download from
            if history.current_round() == 0:
                for item in rarest_order:
                    if item[0] in isect:
                        req_peer = random.choice(item[1])
                        print("piece to download", item[0])
                        print("from", req_peer)
            else:
                for item in rarest_order:
                    if item[0] in isect:
                        # choose the peer from item[1] that has the fastest upload rate
                        ...
        '''

        for peer in peers:
            isect = np_set.intersection(avail_set)
            for item in rarest_order:
                    if item[0] in isect:
                        req_peer = random.choice(item[1])
                        start_block = self.pieces[item[0]]
                        r = Request(self.id, req_peer, item[0], start_block)
                        print("request", r)
                        requests.append(r)
        print(requests)
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

        # To-do:
        # 1. Upload to the k-1 people each turn (k=4 and leave one slot open to unchoke)
        # 2. Round 0: Choose k-1 people at random since there is no download history
        # 3. Post-Round 0 we choose the k-1 people we downloaded the most pieces from
        # 4. Rounds that are multiples of 3, we choose a peer at random that is not in the k-1
        #    to optimistically unchoke

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
