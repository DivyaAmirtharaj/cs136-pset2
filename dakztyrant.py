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

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        
        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        peers.sort(key=lambda p: p.id)
        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
            # More symmetry breaking -- ask for random pieces.
            # This would be the place to try fancier piece-requesting strategies
            # to avoid getting the same thing from multiple peers at a time.
            for piece_id in random.sample(isect, n):
                # aha! The peer has this piece! Request it.
                # which part of the piece do we need next?
                # (must get the next-needed blocks in order)
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
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

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            if round == 0:
                for p in peers:
                    uploads.append(Upload(self.id, p.id, self.up_bw / (len(peers) - 1)))

            gamma = 0.1
            r = 3
            alpha = 0.2

            if round != 0:
                prev_down_history = history.downloads[round - 1]
                download_blocks = {}

                # finding the number of blocks i (self) downloaded from j
                for d in prev_down_history:
                    if d.to_id == self.id:
                        d_id = d.from_id
                        if d_id not in download_blocks:
                            download_blocks[d_id] = d.blocks
                        else:
                            download_blocks[d_id] += d.blocks
                
                prev_up_history = history.uploads[round - 1]
                upload_bws = {}
                # finding the amount that i (self) uploaded to j
                for u in prev_up_history:
                    if u.from_id == self.id:
                        u_id = u.to_id
                        if u_id not in upload_bws:
                            upload_bws[u_id] = u.bw
                        else:
                            upload_bws[u_id] += u.bw
                
                speed_dict = {}

                for p in peers:
                    if p.id in download_blocks.keys():
                        # download speed
                        dij = download_blocks[p.id]
                        unchoked_three_rounds = True

                        if round >= 3:
                            # only need to check the last two rounds because 
                            # if p.id is in the previous download history
                            # then i (self) must have downloaded from j (p.id)
                            for i in range(1, 3):
                                unchoked_this_round = False
                                next_down_history = history.downloads[round - i - 1]
                                for d in next_down_history:
                                    d_from = d.from_id
                                    if d_from == p.id:
                                        unchoked_this_round = True
                                        break
                                
                                if not unchoked_this_round:
                                    unchoked_three_rounds = False
                                    break
                        
                        if p.id in upload_bws.keys():
                            # if i (self) did upload to j 
                            # use the previous upload speed as a baseline
                            uij = upload_bws[p.id]
                        else:
                            # if i (self) did not upload to j
                            # default is the average of the upload bandwidth for i over all j
                            uij = self.up_bw / (len(peers) - 1)
                        
                        # if peer j unchoked i (downloaded from j to i) these last 3 rounds
                        # set the upload bandwidth to 1 - gamma * what it is now
                        if unchoked_three_rounds:
                            uij = (1.0 - gamma) * uij
                        
                        # peer j unchoked peer i during the last round, so set
                        # download speed to the calculated speed
                        speed_dict[p.id] = [dij, uij]
                    else:
                        # if peer j did not unchoke peer i at all (peer i did not download from peer j)
                        # first, we need to estimate the download speed as
                        # the number of pieces j has / 4 (from textbook 5.12)

                        dij = len(p.available_pieces) / 4.0

                        if p in upload_bws.keys():
                            # if i (self) did upload to j but didn't receive a download
                            # increase the upload bandwidth from what it was last
                            uij = (1 + alpha) * uij
                        else:
                            # otherwise, keep the average as a baseline
                            uij = self.up_bw / (len(peers) - 1)

                        speed_dict[p.id] = [dij, uij]

                all_ids = list(speed_dict.keys())
                all_uploads = [vals[1] for vals in list(speed_dict.values())]
                all_speeds = [1.0 * vals[0] / vals[1] for vals in list(speed_dict.values())]               
                zipped_lists = zip(all_speeds, all_ids, all_uploads)
                sorted_triples  = sorted(zipped_lists, reverse=True)
                ranked_tuples = zip(*sorted_triples)
                all_speeds, all_ids, all_uploads = [ list(tuple) for tuple in ranked_tuples]
                print(all_uploads)

                cap = self.up_bw
                ind = 0
                print(all_ids)

                while cap > 0:
                    print(cap)
                    if ind < len(all_ids) and all_ids[ind] in request_ids:
                        print(all_ids[ind])
                        if cap - all_uploads[ind] > 0:
                            uploads.append(Upload(self.id, all_ids[ind], all_uploads[ind]))
                        cap -= all_uploads[ind]
                    elif ind >= len(all_ids):
                        break
                    ind += 1
                    print("index: " + str(ind))
                


            print(request_ids)


            '''

            request = random.choice(requests)
            chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
        '''
        print("uploads: " + str(uploads))
            
        return uploads
