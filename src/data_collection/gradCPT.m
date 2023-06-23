Screen('Preference','SyncTestSettings' ,0.002,50,0.1,5);
warning('off','MATLAB:table:ModifiedAndSavedVarnames')

%% PTB Setup

% Clear the workspace and the screen
sca;
close all;
clear;

% Here we call some default settings for setting up Psychtoolbox
PsychDefaultSetup(2);

% Get the screen numbers. This gives us a number for each of the screens
% attached to our computer.
screens = Screen('Screens');

% To draw we select the maximum of these numbers. So in a situation where we
% have two screens attached to our monitor we will draw to the external
% secondary screen.
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
Screen('BlendFunction', window, 'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA');

% Measure the vertical refresh rate of the monitor
ifi = Screen('GetFlipInterval', window);

% Retreive the maximum priority number and set the PTB priority level
topPriorityLevel = MaxPriority(window);
Priority(topPriorityLevel);

% Length of time and number of frames we will use for each drawing test
numSecs = 1;
numFrames = round(numSecs / ifi);

% Number of frames to wait when specifying good timing. Note: the use of
% wait frames is to show a generalisable coding. For example, by using
% waitframes = 2 one would flip on every other frame. See the PTB
% documentation for details. In what follows we flip every frame.
waitframes = 1;

%% Experiment Setup

infoFile = "C:\Users\HP User\source\repos\attention-monitoring\src\data\gradCPT_sessions\S6_220623\info.json";

% Load session info
jsonString = fileread(infoFile);
info = jsondecode(jsonString);

% Length of time and number of frames we will use for each trial
t_transition = info.stim_transition_time_ms / 1000;
t_static = info.stim_static_time_ms / 1000;
numFrames_transition = round(t_transition / ifi);
numFrames_static = round(t_static / ifi);

% Define parameters for stimulus transition period
waitframes = 4;
numFrameChanges_transition = numFrames_transition / waitframes;
if ~isinteger(numFrameChanges_transition)
    disp("WARNING: The number of frames in the stimulus " + ...
        "transition period is a non-integer multiple of " + ...
        "`waitframes`. The total number of frames shown in" + ...
        "the transition period will be rounded to the " + ...
        "nearest integer multiple of `waitframes`.");
    numFrameChanges_transition = round(numFrameChanges_transition);
end
disp(numFrames_transition)
disp(numFrames_transition * ifi)

%% Run The Experiment

% Get the blocks of trials to complete for this session
blocks = readtable( ...
    info.blocks_file, ...
    'ReadVariableNames', true, ...
    'Delimiter', ',' ...
    );

x = 0;

% Run each block of trials
for k1 = 1:height(blocks)
    % Get the sequence of stimuli to present for this block
    stimSequence = readtable( ...
        blocks.stimSeqFile{k1}, ...
        'ReadVariableNames', true, ...
        'Delimiter', ',' ...
        );

    % Pre-load stimuli and make into textures
    uniqueStimPaths = unique(stimSequence.stimulus_path);
    stimTextures = dictionary;
    for k = 1:length(uniqueStimPaths)
        img = imread(uniqueStimPaths{k});
        [s1, s2, s3] = size(img);
        
        % Check if the image is too big to fit on the screen 
        if s1 > screenYpixels || s2 > screenYpixels
            disp('WARNING! Image is too big to fit on the screen. Rescaling image.');

            % Determine the scaling needed to make the rabbit image fill the whole
            % screen in the y dimension
            maxScaling = screenYpixels / s1;

            % Set the based rectangle size for drawing to the screen
            baseRect = CenterRectOnPointd([0 0 s2 s1] .* maxScaling, xCenter, yCenter);
        end

        % Make the image into a texture and store in dictionary
        imgTexture = Screen('MakeTexture', window, img);
        stimTextures(uniqueStimPaths{k}) = imgTexture;
    end
    
    % Show stimuli
    last_stim = stimSequence.stimulus_path{end};
    vbl = Screen('Flip', window);
    for k2 = 1:height(stimSequence)
        stim = stimSequence.stimulus_path{k2};
        
        % Transition Period
        for k3 = 1:numFrameChanges_transition
            % Linearly increase image opacity over transition period
            contrast = k3 / numFrameChanges_transition;
            Screen( ...
                'DrawTextures', ...
                window, ...
                [stimTextures(last_stim), stimTextures(stim)], ...
                [], baseRect, 0, [], ...
                [1, contrast] ...
                );
            vbl = Screen( ...
                'Flip', ...
                window, ...
                vbl + (waitframes - 0.5) * ifi ...
                );
        end
        % On loop termination: The k2^th stimulus is fully coherent

        disp(vbl)

        % Static Period
        Screen( ...
            'DrawTextures', ...
            window, ...
            stimTextures(stim), ...
            [], baseRect ...
            );
        vbl = Screen( ...
            'Flip', ...
            window, ...
            vbl + (numFrames_static - 0.5) * ifi ...
            );
        
        
        disp(vbl)
        disp(vbl - x)
        x = vbl;

        last_stim = stim;
    end
end

% Set priority back to low.
Priority(0);

% Clear the screen.
sca;