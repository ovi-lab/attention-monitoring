#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2023.1.2),
    on June 19, 2023, at 16:32
If you publish work using this script the most relevant publication is:

    Peirce J, Gray JR, Simpson S, MacAskill M, Höchenberger R, Sogo H, Kastman E, Lindeløv JK. (2019) 
        PsychoPy2: Experiments in behavior made easy Behav Res 51: 195. 
        https://doi.org/10.3758/s13428-018-01193-y

"""

# --- Import packages ---
from psychopy import locale_setup
from psychopy import prefs
from psychopy import plugins
plugins.activatePlugins()
prefs.hardware['audioLib'] = 'ptb'
prefs.hardware['audioLatencyMode'] = '3'
from psychopy import sound, gui, visual, core, data, event, logging, clock, colors, layout
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED,
                                STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)

import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import (sin, cos, tan, log, log10, pi, average,
                   sqrt, std, deg2rad, rad2deg, linspace, asarray)
from numpy.random import random, randint, normal, shuffle, choice as randchoice
import os  # handy system and path functions
import sys  # to get file system encoding

import psychopy.iohub as io
from psychopy.hardware import keyboard

# Run 'Before Experiment' code from code
import argparse
import json
import csv

# Constants
STIM_TRANSITION_TIME = 0.8
STIM_STATIC_TIME = 0.4

DEBUG = 1

parser = argparse.ArgumentParser()
parser.add_argument(
    "-fi",
    "--infoFile",
    help="The path to the info file specifying details of this session.",
    required=True
    )
args = parser.parse_args()
infoFile = args.infoFile

with open(infoFile, "r") as f:
    info = json.load(f)

blocksFile = info["blocks_file"]



# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_thisDir)
# Store info about the experiment session
psychopyVersion = '2023.1.2'
expName = 'gradCPT'  # from the Builder filename that created this script
expInfo = {
    'participant': f"{randint(0, 999999):06.0f}",
    'session': '001',
}
# --- Show participant info dialog --
dlg = gui.DlgFromDict(dictionary=expInfo, sortKeys=False, title=expName)
if dlg.OK == False:
    core.quit()  # user pressed cancel
expInfo['date'] = data.getDateStr()  # add a simple timestamp
expInfo['expName'] = expName
expInfo['psychopyVersion'] = psychopyVersion

# Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
filename = _thisDir + os.sep + u'data/%s_%s_%s' % (expInfo['participant'], expName, expInfo['date'])

# An ExperimentHandler isn't essential but helps with data saving
thisExp = data.ExperimentHandler(name=expName, version='',
    extraInfo=expInfo, runtimeInfo=None,
    originPath='C:\\Users\\HP User\\source\\repos\\attention-monitoring\\src\\data_collection\\gradCPT_lastrun.py',
    savePickle=True, saveWideText=True,
    dataFileName=filename)
# save a log file for detail verbose info
logFile = logging.LogFile(filename+'.log', level=logging.EXP)
logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

endExpNow = False  # flag for 'escape' or other condition => quit the exp
frameTolerance = 0.001  # how close to onset before 'same' frame

# Start Code - component code to be run after the window creation

# --- Setup the Window ---
win = visual.Window(
    size=[1280, 720], fullscr=True, screen=0, 
    winType='pyglet', allowStencil=False,
    monitor='testMonitor', color=[0,0,0], colorSpace='rgb',
    backgroundImage='', backgroundFit='none',
    blendMode='avg', useFBO=True, 
    units='height')
win.mouseVisible = False
# store frame rate of monitor if we can measure it
expInfo['frameRate'] = win.getActualFrameRate()
if expInfo['frameRate'] != None:
    frameDur = 1.0 / round(expInfo['frameRate'])
else:
    frameDur = 1.0 / 60.0  # could not measure, so guess
# --- Setup input devices ---
ioConfig = {}

# Setup iohub keyboard
ioConfig['Keyboard'] = dict(use_keymap='psychopy')

ioSession = '1'
if 'session' in expInfo:
    ioSession = str(expInfo['session'])
ioServer = io.launchHubServer(window=win, **ioConfig)
eyetracker = None

# create a default keyboard (e.g. to check for escape)
defaultKeyboard = keyboard.Keyboard(backend='iohub')

# --- Initialize components for Routine "preBlock" ---

# --- Initialize components for Routine "trial" ---
last_stimulus = visual.ImageStim(
    win=win,
    name='last_stimulus', 
    image='default.png', mask=None, anchor='center',
    ori=0.0, pos=(0, 0), size=(0.5, 0.5),
    color=[1,1,1], colorSpace='rgb', opacity=None,
    flipHoriz=False, flipVert=False,
    texRes=128.0, interpolate=True, depth=-1.0)
transitioning_stimulus = visual.ImageStim(
    win=win,
    name='transitioning_stimulus', 
    image='default.png', mask=None, anchor='center',
    ori=0.0, pos=(0, 0), size=(0.5, 0.5),
    color=[1,1,1], colorSpace='rgb', opacity=1.0,
    flipHoriz=False, flipVert=False,
    texRes=128.0, interpolate=True, depth=-2.0)
static_stimulus = visual.ImageStim(
    win=win,
    name='static_stimulus', 
    image='default.png', mask=None, anchor='center',
    ori=0.0, pos=(0, 0), size=(0.5, 0.5),
    color=[1,1,1], colorSpace='rgb', opacity=None,
    flipHoriz=False, flipVert=False,
    texRes=128.0, interpolate=True, depth=-3.0)

# Create some handy timers
globalClock = core.Clock()  # to track the time since experiment started
routineTimer = core.Clock()  # to track time remaining of each (possibly non-slip) routine 

# set up handler to look after randomisation of conditions etc
blocks = data.TrialHandler(nReps=1.0, method='sequential', 
    extraInfo=expInfo, originPath=-1,
    trialList=data.importConditions(blocksFile),
    seed=None, name='blocks')
thisExp.addLoop(blocks)  # add the loop to the experiment
thisBlock = blocks.trialList[0]  # so we can initialise stimuli with some values
# abbreviate parameter names if possible (e.g. rgb = thisBlock.rgb)
if thisBlock != None:
    for paramName in thisBlock:
        exec('{} = thisBlock[paramName]'.format(paramName))

for thisBlock in blocks:
    currentLoop = blocks
    # abbreviate parameter names if possible (e.g. rgb = thisBlock.rgb)
    if thisBlock != None:
        for paramName in thisBlock:
            exec('{} = thisBlock[paramName]'.format(paramName))
    
    # --- Prepare to start Routine "preBlock" ---
    continueRoutine = True
    # update component parameters for each repeat
    # Run 'Begin Routine' code from code_2
    # Get first and last stimuli shown for this block
    with open(stimSeqFile, "r") as f:
        dictReader = csv.DictReader(f)
        for row in dictReader:
            if dictReader.line_num == 1:
                firstStim = dict(row)
            else:
                pass
        lastStim = dict(row)
    
    # Use the last stimuli to transition to the first
    last_stimulus_path = lastStim["stimulus_path"]
    
    # keep track of which components have finished
    preBlockComponents = []
    for thisComponent in preBlockComponents:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "preBlock" ---
    routineForceEnded = not continueRoutine
    while continueRoutine:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # check for quit (typically the Esc key)
        if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
            core.quit()
            if eyetracker:
                eyetracker.setConnectionState(False)
        
        # check if all components have finished
        if not continueRoutine:  # a component has requested a forced-end of Routine
            routineForceEnded = True
            break
        continueRoutine = False  # will revert to True if at least one component still running
        for thisComponent in preBlockComponents:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "preBlock" ---
    for thisComponent in preBlockComponents:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # the Routine "preBlock" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    trials = data.TrialHandler(nReps=1.0, method='sequential', 
        extraInfo=expInfo, originPath=-1,
        trialList=data.importConditions(stimSeqFile),
        seed=None, name='trials')
    thisExp.addLoop(trials)  # add the loop to the experiment
    thisTrial = trials.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
    if thisTrial != None:
        for paramName in thisTrial:
            exec('{} = thisTrial[paramName]'.format(paramName))
    
    for thisTrial in trials:
        currentLoop = trials
        # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
        if thisTrial != None:
            for paramName in thisTrial:
                exec('{} = thisTrial[paramName]'.format(paramName))
        
        # --- Prepare to start Routine "trial" ---
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from code
        if DEBUG >= 1:
            print(f"current stimulus: {stimulus_path}")
            print(f"last stimulus:    {last_stimulus_path}")
            print("")
        last_stimulus.setImage(last_stimulus_path)
        transitioning_stimulus.setImage(stimulus_path)
        static_stimulus.setImage(stimulus_path)
        # keep track of which components have finished
        trialComponents = [last_stimulus, transitioning_stimulus, static_stimulus]
        for thisComponent in trialComponents:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "trial" ---
        routineForceEnded = not continueRoutine
        while continueRoutine and routineTimer.getTime() < 1.2000000000000002:
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *last_stimulus* updates
            
            # if last_stimulus is starting this frame...
            if last_stimulus.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                last_stimulus.frameNStart = frameN  # exact frame index
                last_stimulus.tStart = t  # local t and not account for scr refresh
                last_stimulus.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(last_stimulus, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'last_stimulus.started')
                # update status
                last_stimulus.status = STARTED
                last_stimulus.setAutoDraw(True)
            
            # if last_stimulus is active this frame...
            if last_stimulus.status == STARTED:
                # update params
                pass
            
            # if last_stimulus is stopping this frame...
            if last_stimulus.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > last_stimulus.tStartRefresh + 0.8-frameTolerance:
                    # keep track of stop time/frame for later
                    last_stimulus.tStop = t  # not accounting for scr refresh
                    last_stimulus.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'last_stimulus.stopped')
                    # update status
                    last_stimulus.status = FINISHED
                    last_stimulus.setAutoDraw(False)
            
            # *transitioning_stimulus* updates
            
            # if transitioning_stimulus is starting this frame...
            if transitioning_stimulus.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                transitioning_stimulus.frameNStart = frameN  # exact frame index
                transitioning_stimulus.tStart = t  # local t and not account for scr refresh
                transitioning_stimulus.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(transitioning_stimulus, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'transitioning_stimulus.started')
                # update status
                transitioning_stimulus.status = STARTED
                transitioning_stimulus.setAutoDraw(True)
            
            # if transitioning_stimulus is active this frame...
            if transitioning_stimulus.status == STARTED:
                # update params
                transitioning_stimulus.setOpacity(t/0.8, log=False)
            
            # if transitioning_stimulus is stopping this frame...
            if transitioning_stimulus.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > transitioning_stimulus.tStartRefresh + 0.8-frameTolerance:
                    # keep track of stop time/frame for later
                    transitioning_stimulus.tStop = t  # not accounting for scr refresh
                    transitioning_stimulus.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'transitioning_stimulus.stopped')
                    # update status
                    transitioning_stimulus.status = FINISHED
                    transitioning_stimulus.setAutoDraw(False)
            
            # *static_stimulus* updates
            
            # if static_stimulus is starting this frame...
            if static_stimulus.status == NOT_STARTED and tThisFlip >= 0.8-frameTolerance:
                # keep track of start time/frame for later
                static_stimulus.frameNStart = frameN  # exact frame index
                static_stimulus.tStart = t  # local t and not account for scr refresh
                static_stimulus.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(static_stimulus, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'static_stimulus.started')
                # update status
                static_stimulus.status = STARTED
                static_stimulus.setAutoDraw(True)
            
            # if static_stimulus is active this frame...
            if static_stimulus.status == STARTED:
                # update params
                pass
            
            # if static_stimulus is stopping this frame...
            if static_stimulus.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > static_stimulus.tStartRefresh + 0.4-frameTolerance:
                    # keep track of stop time/frame for later
                    static_stimulus.tStop = t  # not accounting for scr refresh
                    static_stimulus.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'static_stimulus.stopped')
                    # update status
                    static_stimulus.status = FINISHED
                    static_stimulus.setAutoDraw(False)
            
            # check for quit (typically the Esc key)
            if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):
                core.quit()
                if eyetracker:
                    eyetracker.setConnectionState(False)
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                routineForceEnded = True
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in trialComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "trial" ---
        for thisComponent in trialComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # Run 'End Routine' code from code
        last_stimulus_path = stimulus_path
        # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
        if routineForceEnded:
            routineTimer.reset()
        else:
            routineTimer.addTime(-1.200000)
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'trials'
    
# completed 1.0 repeats of 'blocks'


# --- End experiment ---
# Flip one final time so any remaining win.callOnFlip() 
# and win.timeOnFlip() tasks get executed before quitting
win.flip()

# these shouldn't be strictly necessary (should auto-save)
thisExp.saveAsWideText(filename+'.csv', delim='auto')
thisExp.saveAsPickle(filename)
logging.flush()
# make sure everything is closed down
if eyetracker:
    eyetracker.setConnectionState(False)
thisExp.abort()  # or data files will save again on exit
win.close()
core.quit()
