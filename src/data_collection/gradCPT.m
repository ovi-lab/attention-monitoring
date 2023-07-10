function gradCPT(infoFile, nvargs)

% TODO:
%  - write documentation
%  - validate timing with photodiodes
%  - [DONE] integrate with rest of code
%  - [DONE] send triggers to lablsl
%  - [DONE] Get dia from info file
%  - write command window output to file (?)
%  - implement viewing angle
%  - choose better stimuli
%  - [DONE] link verbose to PTB verbosity
%  - add verbose output that prints session info and start of session info
%  - implement button press recordings
%  - [DONE] add participant directory to info file
%  - ensure timer stays aligned with screen retrace
%  - [DONE] refactor code: for t/s period start times, store all of the expected
%    start time, the actual start time, and whether the presentation
%    deadline was missed.
%  - Fix transition start error
%  - [DONE] make mouse invisible
%  - [DONE] add functionality for ending the session early
%  - [DONE] add try catch block for graceful failing
%  - [DONE] close streams once done
%  - refactoring: abstract certain code blocks to local functions
%  - add button to start experiment
%  - crop images to same size so they keep a consistent resolution

arguments
    infoFile (1,:) {mustBeFile}
    nvargs.streamMarkersToLSL (1,1) logical = false
    nvargs.verbose (1,1) {mustBeInteger} = 0
end

% Wrap all code in function inside try-catch block for graceful failing
try 
    streamMarkersToLSL = nvargs.streamMarkersToLSL;
    verbose = nvargs.verbose;
    
    % Check if necessary toolboxes are on the search path (not rigorous)
    toolboxes = ["liblsl-Matlab", "Psychtoolbox"];
    for k = 1:length(toolboxes)
        paths = strsplit(path, pathsep);
        if ~any(contains(paths, toolboxes(k), 'IgnoreCase', ispc))
            msg = "Could not find the following toolbox on the search" + ...
                " path: " + toolboxes(k);
            ME = MException('gradCPT:toolboxNotFound', msg);
            throw(ME);
        end
    end
    
    % Custom preferences, these are used in the specific study ran by this
    % author. They may be changed or removed at the user's discretion.
    Screen('Preference','SyncTestSettings',0.002,50,0.1,5);
    warning('off','MATLAB:table:ModifiedAndSavedVarnames');

    % Unify the key naming scheme (for getting keyboard inputs)
    KbName('UnifyKeyNames');
    
    % Clear the workspace
    clearvars -except infoFile verbose streamMarkersToLSL;
    
    %% Lab Streaming Layer Setup
    
    if streamMarkersToLSL
        % Load LSL library
        lib = lsl_loadlib();
        
        % Make two new LSL stream outlets for sending markers to LSL: one as
        % timestamps of stimuli, and one as timestamps of key presses
        % (responses)
        if verbose >= 2
            label = "gradCPT: ";
            msg = "Creating new stream_info objects and opening " + ...
                "outlets for two LSL marker streams: one for sending " + ...
                "stimuli timestamps and one for sending key press " + ...
                "timestamps (responses).";
            msg = label + textwrap(msg, 80 - strlength(label));
            fprintf('%s\n', msg{:});
        end
        stimStreamInfo = lsl_streaminfo( ...
            lib, ...
            'stimuli_marker_stream', ...
            'Markers', ...
            1, 0, ...
            'cf_string' ...
            );
        responseStreamInfo = lsl_streaminfo( ...
            lib, ...
            'response_marker_stream', ...
            'Markers', ...
            1, 0, ...
            'cf_string' ...
            );
        stimStreamOutlet = lsl_outlet(stimStreamInfo);
        responseStreamOutlet = lsl_outlet(responseStreamInfo);
    end
    
    %% Psychtoolbox Setup
    
    % Specify verbosity of Psychtoolbox's output
    Screen('Preference', 'Verbosity', double(verbose));
    
    % Clear the screen
    sca;
    close all;
    
    % Here we call some default settings for setting up Psychtoolbox
    PsychDefaultSetup(2);
    
    % Get the screen numbers. This gives us a number for each of the screens
    % attached to our computer.
    screens = Screen('Screens');
    
    % To draw we select the maximum of these numbers. So in a situation 
    % where we have two screens attached to our monitor we will draw to the 
    % external secondary screen.
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
    
    % Retrieve the maximum priority number and set the PTB priority level
    topPriorityLevel = MaxPriority(window);
    Priority(topPriorityLevel);
    
    % Setup KbQueue for getting key presses from the keyboard
    responseKey = KbName('space');
    continueKey = KbName('return');
    quitKey = KbName('ESCAPE');
    KbQueueCreate();
    KbQueueStart();
    
    %% Experiment Setup
    
    % Load session info
    jsonString = fileread(infoFile);
    info = jsondecode(jsonString);
    
    % Define parameters for preparing the stimuli
    dia = info.stim_diameter;
    
    % Length of time and number of frames we will use for each trial
    timeTP = info.stim_transition_time_ms / 1000;
    timeSP = info.stim_static_time_ms / 1000;
    numFramesTP = timeTP / ifi;
    numFramesSP = timeSP / ifi;
    if ~isinteger(numFramesTP) || ~isinteger(numFramesSP)
        if verbose >= 1
            label = "gradCPT-WARNING: ";
            msg = "The desired duration of the transition " + ...
                "and/or static periods cannot be achieved, as it is " + ...
                "not an integer multiple of the duration of one " + ...
                "frame. The duration will be adjusted to the closest " + ...
                "integer multiple of the duration of one frame.";
            msg = label + textwrap(msg, 80 - strlength(label));
            fprintf('\n');
            fprintf('%s\n', msg{:});
        end
        if verbose >= 2
            label = "gradCPT-WARNING: ";
            msg = {
                "Duration of one frame (IFI):", ifi;
                "Desired transition period duration:", timeTP;
                " - Required number of frames:", numFramesTP;
                " - Adjusted duration:" round(numFramesTP) * ifi;
                " - Adjusted number of frames:", round(numFramesTP);
                "Desired static period duration:", timeSP;
                " - Required number of frames:", numFramesSP;
                " - Adjusted duration:" round(numFramesSP) * ifi;
                " - Adjusted number of frames:", round(numFramesSP);
                };
            for row = 1:height(msg)
                fprintf('%s    %-35s %f\n', label, msg{row,1}, msg{row,2});
            end
        end
        numFramesTP = round(numFramesTP);
        numFramesSP = round(numFramesSP);
        timeTP = numFramesTP * ifi;
        timeSP = numFramesSP * ifi;
    end
    
    % Define parameters for stimulus transition period
    waitframes = 2;
    numFrameChanges_transition = numFramesTP / waitframes;
    if ~isinteger(numFrameChanges_transition)
        if verbose >= 1
            label = "gradCPT-WARNING: ";
            msg = "The desired duration of the transition " + ...
                "period cannot be achieved, as the number of frames " + ...
                "shown in the transition period is a non-integer " + ...
                "multiple of `waitframes`. The duration will be " + ...
                "adjusted to the closest value such that the number " + ...
                "of frames shown is an integer multiple of `waitframes`.";
            msg = label + textwrap(msg, 80 - strlength(label));
            fprintf('\n');
            fprintf('%s\n', msg{:});
        end
        if verbose >= 2
            label = "gradCPT-WARNING: ";
            msg = {
                "waitframes:", waitframes;
                "Desired transition period duration:", timeTP;
                " - Required number of frames:", numFramesTP;
                " - Required number of waitframe periods:", ...
                numFrameChanges_transition;
                " - Adjusted duration:", ...
                round(numFrameChanges_transition) * waitframes * ifi;
                " - Adjusted number of frames:", ...
                round(numFrameChanges_transition) * waitframes;
                " - Adjusted number of waitframe periods:", ...
                round(numFrameChanges_transition);
                };
            for row = 1:height(msg)
                fprintf('%s    %-40s %f\n', label, msg{row,1}, msg{row,2});
            end
        end
        numFrameChanges_transition = round(numFrameChanges_transition);
        numFramesTP = numFrameChanges_transition * waitframes;
        timeTP = numFramesTP * ifi;
    end
    
    %% Run The Experiment
    
    % Timestamp start of session
    if streamMarkersToLSL
        stimStreamOutlet.push_sample({'session_start'});
    end
    
    % Get the blocks of trials to complete for this session
    blocks = readtable( ...
        info.blocks_file, ...
        'ReadVariableNames', true, ...
        'Delimiter', ',' ...
        );
    
    % Hide the cursor
    HideCursor(screenNumber);
    
    % Run each block of trials
    for k1 = 1:height(blocks)
        if verbose >= 2
            msg = "== " + blocks.block_name{k1} + " ==";
            fprintf('\n%s\n', msg);
        end
    
        % Display pre-block message and define the pre-block period start 
        % and end times
        Screen('TextSize', window, 70);
        msg = [blocks.pre_block_msg{k1}, '\n'];
        DrawFormattedText(window, msg, 'center', 'center', white);
        pbbStartTime = Screen('flip', window);
        pbbEndTime = pbbStartTime + blocks.pre_block_wait_time(k1);
    
        % Get the sequence of stimuli to present for this block
        stimSequence = readtable( ...
            blocks.stim_sequence_file{k1}, ...
            'ReadVariableNames', true, ...
            'Delimiter', ',' ...
            );
    
        % Pre-load stimuli and make into textures
        uniqueStimPaths = unique(stimSequence.stimulus_path);
        stimTextures = dictionary;
        for k2 = 1:length(uniqueStimPaths)
            % Initialize stimulus texture with a grey background
            stimTexture = Screen( ...
                'MakeTexture', ...
                window,...
                ones(screenYpixels, screenXpixels) .* grey ...
                );
    
            % Load the image, convert to grayscale, and make into a texture
            img = imread(uniqueStimPaths{k2});
            img = rgb2gray(img);
            imgTexture = Screen('MakeTexture', window, img);
    
            % Define destination rectangle to draw the stimulus to
            % (fascilitates rescaling such that the smallest dimension of
            % the stimulus - width or height - is equal to dia)
            [s1, s2, s3] = size(img);
            scale = dia / min([s1, s2]);
            destinationRect = CenterRectOnPointd( ...
                [0 0 s2 s1] .* scale, ...
                xCenter, ...
                yCenter ...
                );
    
            % Scale image and add to stimulus texture
            Screen( ...
                'DrawTexture', ...
                stimTexture, ...
                imgTexture, ...
                [], ...
                destinationRect ...
                );
    
            % Apply a mask to display stimulus through a circular aperture
            maskRect = Screen('Rect', stimTexture);
            apertureRect = CenterRectOnPointd( ...
                [0, 0, dia, dia], ...
                xCenter, ...
                yCenter ...
                );
            Screen( ...
                'Blendfunction', ...
                stimTexture, ...
                GL_ONE, GL_ZERO, ...
                [0 0 0 1] ...
                );
            Screen('FillRect', stimTexture, [0 0 0 0], maskRect);
            Screen('FillOval', stimTexture, [0 0 0 255], apertureRect);
            Screen( ...
                'Blendfunction', ...
                stimTexture, ...
                GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA ...
                );
            
            % Save stimulus to dictionary
            stimTextures(uniqueStimPaths{k2}) = stimTexture;
    
            % Close textures that will no longer be used (for efficiency)
            Screen('Close', imgTexture);
        end
    
        % Wait set amount of time before showing stimuli (allows for breaks
        % between blocks and/or gives time to read pre block message)
        KbEventFlush();
        if blocks.pre_block_wait_time(k1) > 1
            timerWaitframes = round(1 / ifi);
            currentTime = GetSecs();
            timerTotalTime = floor(pbbEndTime - currentTime);
            vbl = pbbEndTime - timerTotalTime - 1;
            for timer = timerTotalTime:-1:0
                % Handle keyboard input
                numEventsAvail = KbEventAvail();
                endPreBlockPeriod = false;
                while numEventsAvail > 0
                    [event, numEventsAvail] = KbEventGet();
                    if event.Pressed
                        switch event.Keycode
                            case continueKey
                                KbEventFlush();
                                endPreBlockPeriod = true;
                                break
                            case quitKey
                                % End the session early
                                KbEventFlush();
                                endSession('early');
                                return
                        end
                    end
                end
                if endPreBlockPeriod
                    break
                end
    
                % Display a timer on the screen
                msg = [blocks.pre_block_msg{k1}, char("\n" + timer)];
                DrawFormattedText(window, msg, 'center', 'center', white);
                vbl = Screen( ...
                    'flip', ...
                    window, ...
                    vbl + (timerWaitframes - 0.5) * ifi ...
                    );
            end
        
            if verbose >= 2
                msg = "Pre-block period time (s): " + (vbl - pbbStartTime);
                fprintf('\n%s\n', msg);
            end
        end
    
        % Timestamp start of block
        if streamMarkersToLSL
            stimStreamOutlet.push_sample({'block_start'});
        end
    
        % Clear the event buffer of the keyboard queue
        KbEventFlush();
    
        % Show stimuli
        last_stim = stimSequence.stimulus_path{end};
        sequenceLength = height(stimSequence);
        % Store the transition and static period start times (measured,
        % expected)
        startTimesTP = zeros(sequenceLength, 2);
        startTimesSP = zeros(sequenceLength, 2);
        % Get the time when to show the first stimulus
        t = Screen('Flip', window);
        t = t + 2.5 * ifi;
        for k2 = 1:sequenceLength
            % At trial start, `t` stores the transition period start time 
            % (that is, calling `Screen('flip')` with this `t` specified as
            % the value of `when` will result in the flip occuring on the 
            % first frame in the transition period, assuming successful 
            % execution).
    
            startTimesTP(k2, 2) = t;
    
            % Select the stimulus to show for this trial
            stim = stimSequence.stimulus_path{k2};
    
            % Transition Period
            % Linearly fade into current stimulus from the last stimulus
            for k3 = 1:numFrameChanges_transition
                % Linearly increase image opacity over transition period
                contrast = k3 / (numFrameChanges_transition + 1);
                Screen( ...
                    'DrawTextures', ...
                    window, ...
                    [stimTextures(last_stim), stimTextures(stim)], ...
                    [], [], 0, [], ...
                    [1, contrast] ...
                    );
                vbl = Screen( ...
                    'Flip', ...
                    window, ...
                    t ...
                    );
                t = t + (waitframes * ifi);
                % Record the estimated start time of the transition period
                % (= end time of previous static period)
                if k3==1
                    startTimesTP(k2, 1) = vbl;
                end
            end
            
            % On termination of above loop, `t` stores the static period 
            % start time (that is, calling `Screen('flip')` with this `t` 
            % specified as the value of `when` will result in the flip 
            % occuring on the first frame in the static period, assuming 
            % successful execution).
    
            startTimesSP(k2, 2) = t;
    
            % Static Period
            % Present the current stimulus (static, fully coherent image)
            Screen( ...
                'DrawTextures', ...
                window, ...
                stimTextures(stim) ...
                );
            vbl = Screen( ...
                'Flip', ...
                window, ...
                t ...
                );
    
            % Record the estimated start time of the static period (= end 
            % time of previous transition period)
            startTimesSP(k2, 1) = vbl;
    
            % Specify the start time of the next trial's transition period
            % (that is, the end of the current trial's static period)
            t = t + (numFramesSP * ifi);
    
            % Additional code to be executed within the stimulus
            % presentation loop, especially computationally expensive
            % operations, should ideally be placed here at the end of the
            % loop. This allows the code to be executed during the static
            % period when the screen is not being updated by Psychtoolbox.
            % For correct behaviour of the loop, ensure execution is
            % completed at latest by time `t` (some time is required for
            % preparing the next stimulus to be presented at time `t`, so
            % the earlier the better). Alternatively, code may also be
            % placed at the beginning of the loop before the transition
            % period.
            % ------------------------------------------------------------|
            % Timestamp transition and static period start times
            if streamMarkersToLSL
                stimStreamOutlet.push_sample( ...
                    {'transition_period_start'}, ...
                    startTimesTP(k2, 1) ...
                    );
                stimStreamOutlet.push_sample( ...
                    {'static_period_start'}, ...
                    startTimesSP(k2, 1) ...
                    );
            end

            % Report estimated timings of previous trial
            if verbose >= 2 && k2 > 1
                reportTrialTimings(k2 - 1)
            end
    
            % Handle input from keyboard
            numEventsAvail = KbEventAvail();
            endStimPresentation = false;
            while numEventsAvail > 0
                [event, numEventsAvail] = KbEventGet();
                if event.Pressed
                    switch event.Keycode
                        case responseKey
                            % Timestamp responses
                            if streamMarkersToLSL
                                responseStreamOutlet.push_sample( ...
                                    {'response'}, ...
                                    event.Time ...
                                    );
                            end
                        case continueKey
                            KbEventFlush();
                            endStimPresentation = true;
                            break
                        case quitKey
                            % End the session early
                            KbEventFlush();
                            endSession('early');
                            return
                    end
                end
            end
            if endStimPresentation
                break
            end
            % ------------------------------------------------------------|
    
            last_stim = stim;
        end
    
        % Flip screen outside of loop to ensure the last stimulus is 
        % presented for the full static period
        vbl = Screen('flip', window, t);
    
        % Report estimated timings of last trial
        if verbose >= 2
            startTimesTP(end+1,:) = [vbl, t];
            reportTrialTimings(k2);
            startTimesTP = startTimesTP(1:end-1,:);
        end
    
        % Close preloaded stimuli at the end of the block
        Screen('Close', values(stimTextures));
    
        % Timestamp end of block
        if streamMarkersToLSL
            stimStreamOutlet.push_sample({'block_stop'});
        end
    end
    
    % Timestamp end of session
    if streamMarkersToLSL
        stimStreamOutlet.push_sample({'session_stop'});
    end
    
    % End the session
    endSession;

% Fail gracefully if any errors occur during function execution
catch ME
    try
        endSession('error');
    catch ME2
        label = "gradCPT-ERROR";
        msg = "An error occured while trying to perform end-of" + ...
            "-session operations. This error may be a result of the " + ...
            "original error that caused the session to end. The error" + ...
            " stacktrace is:";
        msg = label + textwrap(msg, 80 - strlength(label));
        fprintf('%s\n', msg{:});
        disp(getReport(ME2));
        fprintf('\n%s\n\n', "-- End of stacktrace --");
    end
    rethrow(ME);
end

%% Helper Functions

function reportTrialTimings(k)
% Report estimated timings of stimuli for trial k.
    columnLabels = [
        "Measured", ...
        "Expected", ...
        "Error (Measured - Expected)"
        ];
    rowLabels = [
        "Transition Time (ms):";
        "Static Time (ms):";
        "Trial Time (ms):";
        "Transition Period Start Time (ms):";
        "Static Period Start Time (ms):"
        ];
    rowValues = 1000 * [
        startTimesSP(k,:) - startTimesTP(k,:);
        startTimesTP(k+1,:) - startTimesSP(k,:);
        startTimesTP(k+1,:) - startTimesTP(k,:);
        startTimesTP(k,:);
        startTimesSP(k,:)
        ];
    rowValues(:,3) = rowValues(:,1) - rowValues(:,2);

    fprintf('\n%s\n', "-- Trial " + k + " --");
    fprintf('%50s | %14s | %8s\n', columnLabels)
    for row_ = 1:height(rowLabels)
        fprintf('%-35s ', rowLabels(row_));
        fprintf('%14.4f | %14.4f | %8.4f\n', rowValues(row_,:));
    end        
end

function endSession(type, printout)
% Perform necessary operations for ending the gradCPT session gracefully.
%   type {mustBeMember(type,{'normal','early','error'})} = 'normal'
%   printout {mustBeText} = ''

    if nargin < 2
        printout = '';
    end
    if nargin < 1
        type = 'normal';
    end
    
    if any(strcmp(type, {'early', 'error'})) && verbose >= 1
        fprintf('\n%s\n\n', "== gradCPT: ENDING SESSION EARLY ==");
    end
    if strcmp(type, 'error') && verbose >= 1
        label = "gradCPT-ERROR: ";
        msg = "The session has ended due to an error. " + ...
            "Attempting to end the session gracefully...";
        msg = label + textwrap(msg, 80-strlength(label));
        fprintf('%s\n', msg{:});
    end

    if ~strcmp(printout, '')
        disp(printout);
    end

    if verbose >= 2
        label = "gradCPT: ";
        msg = "Attempting to perform end-of-session operations...";
        msg = label + textwrap(msg, 80 - strlength(label));
        fprintf('%s\n', msg);
    end
    if streamMarkersToLSL
        stimStreamOutlet.delete();
        responseStreamOutlet.delete();
    end
    KbQueueRelease();
    KbReleaseWait();
    ShowCursor([], screenNumber);
    sca;
    Priority(0);
    if verbose >= 2
        label = "gradCPT: ";
        msg = "Successfully performed end-of-session operations.";
        msg = label + textwrap(msg, 80 - strlength(label));
        fprintf('%s\n\n', msg);
    end
end

end