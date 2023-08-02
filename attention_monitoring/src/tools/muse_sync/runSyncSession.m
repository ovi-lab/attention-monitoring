function recordingFile = runSyncSession(dataDir, nvargs)
    % Run a muse synchronisation session

    arguments
        dataDir (1,:) {mustBeTextScalar} = pwd
        nvargs.verbose (1,1) {mustBeInteger} = 0
        nvargs.autoRecord (1,1) logical = false;
        nvargs.recordingLength (1,1) double = 10;
        nvargs.recordingName (1,:) {mustBeTextScalar} = "muse_sync_data.xdf"
    end

    autoRecord = nvargs.autoRecord;
    recordingLength = nvargs.recordingLength;
    recordingName = nvargs.recordingName;

    log = Logger(nvargs.verbose, "runSyncSession");

    Screen('Preference','SyncTestSettings',0.002,50,0.1,5);
    try
        %% Psychtoolbox Setup
        
        % Specify verbosity of Psychtoolbox's output
        Screen('Preference', 'Verbosity', double(log.verbose));
        
        % Clear the screen
        sca;
        close all;
        
        % Here we call some default settings for setting up Psychtoolbox
        PsychDefaultSetup(2);
        
        % Get the screen numbers. This gives us a number for each of the
        % screens attached to our computer.
        screens = Screen('Screens');
        
        % To draw we select the maximum of these numbers. So in a situation
        % where we have two screens attached to our monitor we will draw to
        % the external secondary screen.
        screenNumber = max(screens);
        
        % Define black and white (white will be 1 and black 0)
        white = WhiteIndex(screenNumber);
        black = BlackIndex(screenNumber);
        grey = white / 2;
        
        % Open an on screen window using PsychImaging and color it grey.
        [window, windowRect] = PsychImaging('OpenWindow', screenNumber, grey);
        
        % Get the size of the on screen window
        [screenXpixels, screenYpixels] = Screen('WindowSize', window);
        
        % Get the centre coordinate of the window
        [xCenter, yCenter] = RectCenter(windowRect);
        
        % Set up alpha-blending for smooth (anti-aliased) lines
        Screen( ...
            'BlendFunction', ...
            window, ...
            'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA' ...
            );
        
        % Measure the vertical refresh rate of the monitor
        ifi = Screen('GetFlipInterval', window);
        
        % Retrieve the maximum priority number and set the PTB priority
        % level
        topPriorityLevel = MaxPriority(window);
        Priority(topPriorityLevel);
        
        % Setup KbQueue for getting key presses from the keyboard
        responseKey = KbName('space');
        continueKey = KbName('return');
        quitKey = KbName('ESCAPE');
        KbQueueCreate();
        KbQueueStart();
    
        %% LSL Setup
    
        % Setup the LSL Stream
        log.print("Setting up the LSL Stream.", 2);
        lib = lsl_loadlib();
        streamInfo = lsl_streaminfo( ...
            lib, ...
            'museSync_markers', ...
            'Markers', ...
            1, 0, ...
            'cf_string' ...
            );
        streamOutlet = lsl_outlet(streamInfo);

        % Setup LabRecorder
        log.print("Setting up LabRecorder", 2);
        [~, baseFileName, ~] = fileparts(recordingName);
        template = baseFileName + ".xdf";
        k = 1;
        while isfile(fullfile(dataDir, template))
            template = baseFileName + "_" + k + ".xdf";
            k = k + 1;
        end
        pathToRecordingFile = fullfile(dataDir, template);
        log.print( ...
            "Selected recording path: " + pathToRecordingFile, ...
            2, ...
            "literal", true ...
            );
        lr = setupLR(dataDir, template);

        %% Presentation
        
        % Define the starting time of the presentation and when to
        % automatically start recording (if applicable)
        t = ceil(GetSecs()) + 2.5 * ifi;
        autoStartTime = t + 3;

        % Define the two colours that the screen will alternate between
        colors = [black, white];
        k = 1;

        % Initialize `recordingFile` as empty string, which is returned if
        % a recording doesn't get made before the presentation ends.
        recordingFile = "";
        
        % Run presentation
        stopPresentation = false;
        recordingHasStarted = false;
        msg = 'Waiting to start recording.';
        while ~stopPresentation
    
            % Fill screen with a solid colour, and display a message
            Screen('FillRect', window, colors(k));
            DrawFormattedText( ...
                window, ...
                char(msg), ...
                'center', 'center', ...
                colors(1 + (k==1)) ...
                );
            vbl = Screen('Flip', window, t);
    
            % Push timestamp of screen colour change to LSL
            streamOutlet.push_sample({'color_switch'}, vbl);

            % Switch colors after every period. For the first 2 seconds of
            % the recording the period is 0.5s, otherwise it is 1s.
            if recordingHasStarted && t <= autoStartTime + 2
                p = 0.5;
            else
                p = 1;
            end
            t = t + p;
            k = 1 + (k == 1);            

            % Start the recording at the appropriate time.
            if ~recordingHasStarted
                if autoRecord
                    % Tell LabRecorder to start recording after the start
                    % time has been reached.
                    if vbl >= autoStartTime
                        log.print("Starting recording on LabRecorder", 2);
                        writeline(lr, 'start');
                        recordingHasStarted = true;
                    end
                else
                    % Check whether LabRecorder has created an xdf file for
                    % this session. Assume the first time this file is
                    % found corresponds to the start time of the recording.
                    if isfile(pathToRecordingFile)
                        log.print("Found a recording file", 2);
                        recordingHasStarted = true;
                    end
                end

                % Perform start of recording operations
                if recordingHasStarted
                    msg = "Recording (~" + recordingLength + "s)";
                    
                    % End the recording after specified time.
                    log.print( ...
                        "Ending recording in about " + ...
                        recordingLength + " seconds.", ...
                        2 ...
                        );
                    recordingEndTime = t + recordingLength;
                end
            end

            % If the recording end time has been reached, stop recording
            % and end the session
            if recordingHasStarted && vbl > recordingEndTime
                log.print("Recording done, ending session.", 2);
                pause(0.5);
                writeline(lr, 'stop');
                pause(1);
                recordingFile = pathToRecordingFile;
                stopPresentation = true;
            end
            
            % Handle keyboard input
            numEventsAvail = KbEventAvail();
            while numEventsAvail > 0
                [event, numEventsAvail] = KbEventGet();
                if event.Pressed && event.Keycode == quitKey
                    stopPresentation = true;
                    break
                end
            end
        end
    
        % End the session
        endSession;
    
    % Fail gracefully if there are any errors during presentation
    catch ME
        try
            endSession('error');
        catch ME2
            msg = "An error occured while trying to perform end-of" + ...
                "-session operations. This error may be a result of " + ...
                "the original error that caused the session to end. " + ...
                "The error stacktrace is:\n";
            log.print(msg, "labelSuffix", "-ERROR");
            disp(getReport(ME2));
            msg = "\n-- End of stacktrace --\n\n";
            log.print(msg, "labelSuffix", "-ERROR");
        end
        rethrow(ME);
    end
    
    function endSession(type, printout)
    % Perform necessary operations for ending sync session gracefully.
    %   type {mustBeMember(type,{'normal','early','error'})} = 'normal'
    %   printout {mustBeText} = ''
    
        % Set default argument values
        if nargin < 2
            printout = '';
        end
        if nargin < 1
            type = 'normal';
        end
        
        if any(strcmp(type, {'early', 'error'}))
            log.print("\n== MUSESYNC: ENDING SESSION EARLY ==\n\n", 1);
        end
        if strcmp(type, 'error')
            msg = "The session has ended due to an error. " + ...
                "Attempting to end the session gracefully...";
            log.print(msg, 1, "labelSuffix", "-ERROR");
        end
    
        if ~strcmp(printout, '')
            disp(printout);
        end
    
        msg = "Attempting to perform end-of-session operations...";
        log.print(msg, 2)
    
        streamOutlet.delete();
        KbQueueRelease();
        ShowCursor([], screenNumber);
        sca;
        Priority(0);
    
        msg = "Successfully performed end-of-session operations.";
        log.print(msg, 2);
    end
end