import datetime

import numpy as np

import acquisition
import include.preRun as preRun
import plotAcquisition
import plotNavigation
import plotTracking
import postNavigation
import tracking


# import plotNavigation
# import plotTracking
# import postNavigation
# import tracking


# ./postProcessing.m

# Script postProcessing.m processes the raw signal from the specified data
# file (in settings) operating on blocks of 37 seconds of data.

# First it runs acquisition code identifying the satellites in the file,
# then the code and carrier for each of the satellites are tracked, storing
# the 1msec accumulations.  After processing all satellites in the 37 sec
# data block, then postNavigation is called. It calculates pseudoranges
# and attempts a position solutions. At the end plots are made for that
# block of data.

#                         THE SCRIPT "RECIPE"

# The purpose of this script is to combine all parts of the software
# receiver.

# 1.1) Open the data file for the processing and seek to desired point.

# 2.1) Acquire satellites

# 3.1) Initialize channels (preRun.m).
# 3.2) Pass the channel structure and the file identifier to the tracking
# function. It will read and process the data. The tracking results are
# stored in the trackResults structure. The results can be accessed this
# way (the results are stored each millisecond):
# trackResults(channelNumber).XXX(fromMillisecond : toMillisecond), where
# XXX is a field name of the result (e.g. I_P, codePhase etc.)

# 4) Pass tracking results to the navigation solution function. It will
# decode navigation messages, find satellite positions, measure
# pseudoranges and find receiver position.

# 5) Plot the results.


def postProcessing(*args, **kwargs):
    nargin = len(args)

    ## Initialization =========================================================
    print 'Starting processing...'

    if nargin == 1:
        settings = args[0]
        fileNameStr = settings.fileName
    elif nargin == 2:
        fileNameStr, settings = args
        if ~isinstance(fileNameStr, str):
            raise TypeError('File name must be a string')
    else:
        raise Exception('Incorrect number of arguments')
    try:
        with open(fileNameStr, 'rb') as fid:

            # If success, then process the data
            # Move the starting point of processing. Can be used to start the
            # signal processing at any point in the data record (e.g. good for long
            # records or for signal processing in blocks).
            fid.seek(settings.skipNumberOfBytes, 0)
            ## Acquisition ============================================================
            # Do acquisition if it is not disabled in settings or if the variable
            # acqResults does not exist.
            if not settings.skipAcquisition or 'acqResults' not in globals():
                # Find number of samples per spreading code
                samplesPerCode = long(round(settings.samplingFreq / (settings.codeFreqBasis / settings.codeLength)))

                # frequency estimation
                data = np.fromfile(fid, settings.dataType, 11 * samplesPerCode)

                print '   Acquiring satellites...'
                acqResults = acquisition.acquisition(data, settings)

                plotAcquisition.plotAcquisition(acqResults)
            ## Initialize channels and prepare for the run ============================
            # Start further processing only if a GNSS signal was acquired (the
            # field FREQUENCY will be set to 0 for all not acquired signals)
            if np.any(acqResults.carrFreq):
                channel = preRun.preRun(acqResults, settings)

                preRun.showChannelStatus(channel, settings)
            else:
                # No satellites to track, exit
                print 'No GNSS signals detected, signal processing finished.'
                trackResults = None

            ## Track the signal =======================================================
            startTime = datetime.datetime.now()

            print '   Tracking started at %s' % startTime.strftime('%X')
            try:
                trackResults = np.load('trackingResults_python.npy')
            except IOError:
                trackResults, channel = tracking.tracking(fid, channel, settings)
                np.save('trackingResults_python', trackResults)

            print '   Tracking is over (elapsed time %s s)' % (datetime.datetime.now() - startTime).total_seconds()
            # Auto save the acquisition & tracking results to a file to allow
            # running the positioning solution afterwards.
            print '   Saving Acq & Tracking results to file "trackingResults.mat"'
            ## Calculate navigation solutions =========================================
            print '   Calculating navigation solutions...'
            try:
                navSolutions = np.load('navSolutions_python.npy')
            except IOError:
                navSolutions, eph = postNavigation.postNavigation(trackResults, settings)
                np.save('navSolutions_python', navSolutions)

            print '   Processing is complete for this data block'
            # return
            # savemat('trackingResults_from_python',
            #         {'trackResults': trackResults,
            #          'settings': settings,
            #          'acqResults': acqResults,
            #          'channel': channel,
            #          'navSolutions': navSolutions})

            ## Plot all results ===================================================
            print '   Plotting results...'
            # TODO
            # turn off tracking plots for now
            if not settings.plotTracking:
                plotTracking.plotTracking(range(settings.numberOfChannels), trackResults, settings)
            plotNavigation.plotNavigation(navSolutions, settings)
            print 'Post processing of the signal is over.'
    except IOError as e:
        # Error while opening the data file.
        print 'Unable to read file "%s": %s.' % (settings.fileName, e)


if __name__ == '__main__':
    postProcessing()
