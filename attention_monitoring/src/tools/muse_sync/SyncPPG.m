% TODO: add support for running without LR

classdef SyncPPG < SyncSession
    methods (Access = protected, Hidden)
        function [result, endedEarly] = runProcedure( ...
                obj, markerOutlet, lr, recordData, autoStart, ...
                recordingLength ...
                )

            Screen('Preference','SyncTestSettings',0.002,50,0.1,5);

            %% Psychtoolbox Setup

            obj.log.print("Setting up Psychtoolbox.", 2);
            
            % Specify verbosity of Psychtoolbox's output
            Screen('Preference', 'Verbosity', double(obj.log.verbose));
            
            % Clear the screen
            sca;
            close all;
            
            % Here we call some default settings for setting up
            % Psychtoolbox
            PsychDefaultSetup(2);
            
            % Get the screen numbers. This gives us a number for each
            % of the screens attached to our computer.
            screens = Screen('Screens');
            
            % To draw we select the maximum of these numbers. So in a
            % situation where we have two screens attached to our
            % monitor we will draw to the external secondary screen.
            screenNumber = max(screens);
            
            % Define black and white (white will be 1 and black 0)
            white = WhiteIndex(screenNumber);
            black = BlackIndex(screenNumber);
            grey = white / 2;
            
            % Open an on screen window using PsychImaging and color it
            % grey.
            [window, windowRect] = PsychImaging( ...
                'OpenWindow', ...
                screenNumber, ...
                grey ...
                );
            
            % Set up alpha-blending for smooth (anti-aliased) lines
            Screen( ...
                'BlendFunction', ...
                window, ...
                'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA' ...
                );
            
            % Measure the vertical refresh rate of the monitor
            ifi = Screen('GetFlipInterval', window);
            
            % Retrieve the maximum priority number and set the PTB
            % priority level
            topPriorityLevel = MaxPriority(window);
            Priority(topPriorityLevel);
            
            % Setup KbQueue for getting key presses from the keyboard
            quitKey = KbName('ESCAPE');
            KbQueueCreate();
            KbQueueStart();
    
            %% Presentation
            
            obj.log.print("Starting the trigger presentation.", 2);

            % Define the starting time of the presentation and when to
            % automatically start recording (if applicable)
            t = ceil(GetSecs()) + 2.5 * ifi;
            autoStartTime = t + 3;
    
            % Define the two colours that the screen will alternate
            % between
            colors = [black, white];
            k = 1;
    
            % Initialize `result` as false, which is returned if the
            % procedure does not successfully complete.
            result = false;
            endedEarly = true;
            
            % Run presentation
            stopPresentation = false;
            recordingHasStarted = false;
            msg = 'Waiting to start recording.';
            while ~stopPresentation
        
                % Fill screen with a solid colour, and display a
                % message
                Screen('FillRect', window, colors(k));
                DrawFormattedText( ...
                    window, ...
                    char(msg), ...
                    'center', 'center', ...
                    colors(1 + (k==1)) ...
                    );
                vbl = Screen('Flip', window, t);
        
                % Push timestamp of screen colour change to LSL
                markerOutlet.push_sample({'color_switch'}, vbl);
    
                % Switch colors after every period. For the first 2
                % seconds of the recording the period is 0.5s,
                % otherwise it is 1s.
                if recordingHasStarted && t <= autoStartTime + 2
                    p = 0.25;
                else
                    p = 0.5;
                end
                t = t + p;
                k = 1 + (k == 1);            
    
                % Start the recording at the appropriate time.
                if ~recordingHasStarted
                    if autoStart
                        % Tell LabRecorder to start recording after the
                        % start time has been reached.
                        if vbl >= autoStartTime
                            obj.log.print( ...
                                "Starting recording on LabRecorder",...
                                2 ...
                                );
                            writeline(lr, 'start');
                            recordingHasStarted = true;
                        end
                    else
                        % Check whether LabRecorder has created an xdf
                        % file for this session. Assume the first time
                        % this file is found corresponds to the start
                        % time of the recording.
                        if isfile(obj.recordingFile)
                            obj.log.print("Found a recording file", 2);
                            recordingHasStarted = true;
                        end
                    end
    
                    % Perform start of recording operations
                    if recordingHasStarted
                        msg = "Recording (~" + recordingLength + "s)";
                        
                        % End the recording after specified time.
                        obj.log.print( ...
                            "Ending recording in about " + ...
                            recordingLength + " seconds.", ...
                            2 ...
                            );
                        recordingEndTime = t + recordingLength;
                    end
                end
    
                % If the recording end time has been reached, stop
                % recording and end the session
                if recordingHasStarted && vbl > recordingEndTime
                    obj.log.print( ...
                        "Recording done, ending session.", ...
                        2 ...
                        );
                    pause(0.5);
                    writeline(lr, 'stop');
                    pause(1);

                    result = true;
                    endedEarly = false;
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
        end

        function atEndOfSession(obj)
            arguments
                obj
            end
            atEndOfSession@SyncSession(obj);

            KbQueueRelease();
            sca;
            Priority(0);
        end
    end
end