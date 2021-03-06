import numpy as np

import initSettings


# navPartyChk.m
def navPartyChk(ndat=None, *args, **kwargs):
    # This function is called to compute and status the parity bits on GPS word.
    # Based on the flowchart in Figure 2-10 in the 2nd Edition of the GPS-SPS
    # Signal Spec.

    # status = navPartyChk(ndat)

    #   Inputs:
    #       ndat        - an array (1x32) of 32 bits represent a GPS navigation
    #                   word which is 30 bits plus two previous bits used in
    #                   the parity calculation (-2 -1 0 1 2 ... 28 29)

    #   Outputs:
    #       status      - the test value which equals EITHER +1 or -1 if parity
    #                   PASSED or 0 if parity fails.  The +1 means bits #1-24
    #                   of the current word have the correct polarity, while -1
    #                   means the bits #1-24 of the current word must be
    #                   inverted.

    # In order to accomplish the exclusive or operation using multiplication
    # this program represents a '0' with a '-1' and a '1' with a '1' so that
    # the exclusive or table holds true for common data operations

    #	a	b	xor 			a	b	product
    #  --------------          -----------------
    #	0	0	 1			   -1  -1	   1
    #	0	1	 0			   -1   1	  -1
    #	1	0	 0			    1  -1	  -1
    #	1	1	 1			    1   1	   1

    # --- Check if the data bits must be inverted ------------------------------
    if ndat[1] != 1:
        ndat[2:26] *= (-1)

    # --- Calculate 6 parity bits ----------------------------------------------
    # The elements of the ndat array correspond to the bits showed in the table
    # 20-XIV (ICD-200C document) in the following way:
    # The first element in the ndat is the D29* bit and the second - D30*.
    # The elements 3 - 26 are bits d1-d24 in the table.
    # The elements 27 - 32 in the ndat array are the received bits D25-D30.
    # The array "parity" contains the computed D25-D30 (parity) bits.
    parity = np.zeros(6)
    parity[0] = ndat[0] * ndat[2] * ndat[3] * ndat[4] * ndat[6] * \
                ndat[7] * ndat[11] * ndat[12] * ndat[13] * ndat[14] * \
                ndat[15] * ndat[18] * ndat[19] * ndat[21] * ndat[24]

    parity[1] = ndat[1] * ndat[3] * ndat[4] * ndat[5] * ndat[7] * \
                ndat[8] * ndat[12] * ndat[13] * ndat[14] * ndat[15] * \
                ndat[16] * ndat[19] * ndat[20] * ndat[22] * ndat[25]

    parity[2] = ndat[0] * ndat[2] * ndat[4] * ndat[5] * ndat[6] * \
                ndat[8] * ndat[9] * ndat[13] * ndat[14] * ndat[15] * \
                ndat[16] * ndat[17] * ndat[20] * ndat[21] * ndat[23]

    parity[3] = ndat[1] * ndat[3] * ndat[5] * ndat[6] * ndat[7] * \
                ndat[9] * ndat[10] * ndat[14] * ndat[15] * ndat[16] * \
                ndat[17] * ndat[18] * ndat[21] * ndat[22] * ndat[24]

    parity[4] = ndat[1] * ndat[2] * ndat[4] * ndat[6] * ndat[7] * \
                ndat[8] * ndat[10] * ndat[11] * ndat[15] * ndat[16] * \
                ndat[17] * ndat[18] * ndat[19] * ndat[22] * ndat[23] * \
                ndat[25]

    parity[5] = ndat[0] * ndat[4] * ndat[6] * ndat[7] * ndat[9] * \
                ndat[10] * ndat[11] * ndat[12] * ndat[14] * ndat[16] * \
                ndat[20] * ndat[23] * ndat[24] * ndat[25]

    # --- Compare if the received parity is equal the calculated parity --------
    if (parity == ndat[26:]).sum() == 6:
        # Parity is OK. Function output is -1 or 1 depending if the data bits
        # must be inverted or not. The "ndat[2]" is D30* bit - the last  bit of
        # previous subframe.
        status = -1 * ndat[1]

    else:
        # Parity failure
        status = 0

    return status


# ./findPreambles.m
def findPreambles(trackResults=None, settings=None, *args, **kwargs):
    # findPreambles finds the first preamble occurrence in the bit stream of
    # each channel. The preamble is verified by check of the spacing between
    # preambles (6sec) and parity checking of the first two words in a
    # subframe. At the same time function returns list of channels, that are in
    # tracking state and with valid preambles in the nav data stream.

    # [firstSubFrame, activeChnList] = findPreambles(trackResults, settings)

    #   Inputs:
    #       trackResults    - output from the tracking function
    #       settings        - Receiver settings.

    #   Outputs:
    #       firstSubframe   - the array contains positions of the first
    #                       preamble in each channel. The position is ms count
    #                       since start of tracking. Corresponding value will
    #                       be set to 0 if no valid preambles were detected in
    #                       the channel.
    #       activeChnList   - list of channels containing valid preambles

    # Preamble search can be delayed to a later point in the tracking results
    # to avoid noise due to tracking loop transients
    searchStartOffset = 0

    # --- Initialize the firstSubFrame array -----------------------------------
    firstSubFrame = np.zeros(settings.numberOfChannels, dtype=int)

    # --- Generate the preamble pattern ----------------------------------------
    preamble_bits = np.r_[1, - 1, - 1, - 1, 1, - 1, 1, 1]

    # "Upsample" the preamble - make 20 vales per one bit. The preamble must be
    # found with precision of a sample.
    preamble_ms = np.kron(preamble_bits, np.ones(20))

    # --- Make a list of channels excluding not tracking channels --------------
    activeChnList = (trackResults.status != '-').nonzero()[0]

    # === For all tracking channels ...
    for channelNr in range(len(activeChnList)):
        ## Correlate tracking output with preamble ================================
        # Read output from tracking. It contains the navigation bits. The start
        # of record is skiped here to avoid tracking loop transients.
        bits = trackResults[channelNr].I_P[searchStartOffset:].copy()

        bits[bits > 0] = 1

        bits[bits <= 0] = - 1

        # have to zero pad the preamble so that they are the same length
        tlmXcorrResult = np.correlate(bits,
                                      np.pad(preamble_ms, (0, bits.size - preamble_ms.size), 'constant'),
                                      mode='full')

        ## Find all starting points off all preamble like patterns ================
        # clear('index')
        # clear('index2')
        xcorrLength = (len(tlmXcorrResult) + 1) / 2

        index = (np.abs(tlmXcorrResult[xcorrLength - 1:xcorrLength * 2]) > 153).nonzero()[0] + searchStartOffset

        ## Analyze detected preamble like patterns ================================
        for i in range(len(index)):
            # --- Find distances in time between this occurrence and the rest of
            # preambles like patterns. If the distance is 6000 milliseconds (one
            # subframe), the do further verifications by validating the parities
            # of two GPS words
            index2 = index - index[i]

            if (index2 == 6000).any():
                # === Re-read bit vales for preamble verification ==============
                # Preamble occurrence is verified by checking the parity of
                # the first two words in the subframe. Now it is assumed that
                # bit boundaries a known. Therefore the bit values over 20ms are
                # combined to increase receiver performance for noisy signals.
                # in Total 62 bits mast be read :
                # 2 bits from previous subframe are needed for parity checking;
                # 60 bits for the first two 30bit words (TLM and HOW words).
                # The index is pointing at the start of TLM word.
                bits = trackResults[channelNr].I_P[index[i] - 40:index[i] + 20 * 60].copy()

                bits = bits.reshape(20, -1, order='F')

                bits = bits.sum(0)

                bits[bits > 0] = 1

                bits[bits <= 0] = - 1

                if navPartyChk(bits[:32]) != 0 and navPartyChk(bits[30:62]) != 0:
                    # Parity was OK. Record the preamble start position. Skip
                    # the rest of preamble pattern checking for this channel
                    # and process next channel.
                    firstSubFrame[channelNr] = index[i]

                    break
        # Exclude channel from the active channel list if no valid preamble was
        # detected
        if firstSubFrame[channelNr] == 0:
            # Exclude channel from further processing. It does not contain any
            # valid preamble and therefore nothing more can be done for it.
            activeChnList = np.setdiff1d(activeChnList, channelNr)

            print 'Could not find valid preambles in channel %2d !' % channelNr
    return firstSubFrame, activeChnList


if __name__ == '__main__':
    trackResults = np.load('trackingResults_python.npy')
    findPreambles(trackResults, initSettings.Settings())
