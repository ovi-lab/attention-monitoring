% TODO: refactor to follow thing from forum post

classdef SyncAudioEEG < SyncSession
    methods (Access = protected, Hidden)
        function [result, endedEarly] = runProcedure( ...
                obj, markerOutlet, lr, recordData, autoStart, ...
                recordingLength ...
                )

            reqLatencyClass = 2;
            numchannels = 1;

            % Setup PsychToolBox
            PsychPortAudio('Verbosity', double(obj.log.verbose));
            PsychDefaultSetup(2);

            % Setup KbQueue for getting key presses from the keyboard
            quitKey = KbName('ESCAPE');
            KbQueueCreate();
            KbQueueStart();

            % Load PsychPortAudio driver in low latency mode
            InitializePsychSound(1);

            % Open device and get the playback sampling rate
            pahandle = PsychPortAudio('Open', ...
                [], [], ...
                reqLatencyClass, ...
                [], ...
                numchannels ...
                );
            status = PsychPortAudio('GetStatus', pahandle);
            SR = status.SampleRate;

            % Define the audio trigger, including the frequency of the tone
            % in Hz and the duration in seconds.
            freq = 200;
            duration = 1;
            trigData = MakeBeep(freq, duration, SR);
            trig = PsychPortAudio('CreateBuffer', [], trigData);
            % Define another trigger that is played `numSyncTrigs` times at
            % the beginning of the test for synchronization. The total
            % duration of all the sync triggers is equal to `duration`.
            numSyncTrigs = 2;
            syncTrigData = MakeBeep(freq, duration / numSyncTrigs, SR);
            syncTrig = PsychPortAudio('CreateBuffer', [], syncTrigData);

            % Define a schedule for when to play triggers. Specified as
            % timestamps in seconds after recording start.
            PsychPortAudio('UseSchedule', pahandle, 1);
            % In one period, trigger is played for `duration` seconds and
            % then wait for `duration` seconds.
            period = 2 * duration;
            % Play the sync trigger `numSyncTrigs` times, followed by the
            % normal triggers for the rest of the test
            trigSchedule = [
                0:(period / numSyncTrigs):period, ...
                (2 * period):period:recordingLength
                ];
            % Delay by some time after start time to ensure all triggers
            % get played
            delay = 1;
            trigSchedule = trigSchedule + delay;
            % Ensure that the recording length is long enough to play at
            % least the sync triggers and one trigger
            if trigSchedule(end) + period - delay < recordingLength
                msg = "The requested recording Length is too short " + ...
                    "since it is not enough time to send all " + ...
                    "syncronization triggers as well as at least one" + ...
                    "normal trigger. Session will continue with " + ...
                    "undefined behavior.";
                obj.log.print(msg, 1, "labelSuffix", "-ERROR");
            end
            % Get schedule as relative delays to previous sound
            relTrigSchedule = [trigSchedule(1), diff(trigSchedule)];
            
            % Define a wrapper method to add the k^th trigger to be played
            % to the the PsychPortAudio Schedule (like a FIFO "playlist").
            function addToScheduleWrapper(k)
                delayCmd = -(1+8);

                if k <= numSyncTrigs
                    bufferItem = syncTrig;
                else
                    bufferItem = trig;
                end
                [s1, ~] = PsychPortAudio( ...
                    'AddToSchedule', ...
                    pahandle, ...
                    delayCmd, ...
                    relTrigSchedule(k) ...
                    );
                [s2, ~] = PsychPortAudio( ...
                    'AddToSchedule', ...
                    pahandle, ...
                    bufferItem ...
                    );

                if ~(s1 && s2)
                    msg = "Failed to add trigger number " + k + ...
                        " to the schedule. Continuing session...";
                    obj.log.print(msg, 1, "labelSuffix", "-WARNING");
                end
            end

            % Don't add all the triggers to the PsychPortAudio Schedule
            % yet. Add up to `bufferSize` triggers right now, then the rest
            % will be added one by one as the triggers get sent.
            bufferSize = 32;
            for k = 1:min(bufferSize, numel(trigSchedule))
                addToScheduleWrapper(k);
            end

            % Start the test, recording the data if desired
            if autoStart
                msg = "Starting test (~" + recordingLength + "s)";
                obj.log.print(msg, 2);
            else
                msg = "Ready to start test, press any key to start.";
                obj.log.print(msg);
                KbStrokeWait();
                msg = "Starting test (~" + recordingLength + "s)";
                obj.log.print(msg, 2);
            end
            if recordData
                msg = "Starting recording on LabRecorder.";
                obj.log.print(msg, 2);
                writeline(lr, 'start');
                pause(0.5);
            end
            startTime = GetSecs();

            % Start sending the triggers
            t = PsychPortAudio('Start', pahandle, [], startTime, 1);

            % Get the trigger schedule relative to the time when the first
            % trigger was sent.
            absTrigSchedule = t + trigSchedule;

            endTestEarly = false;
            for k = 1:numel(absTrigSchedule)
                % Wait until about the time when the trigger is sent
                WaitSecs('UntilTime', absTrigSchedule(k));

                % Send the timestamp of when the trigger was scheduled to
                % be sent
                % TODO: change to get the estimated real time it played
                markerOutlet.push_sample( ...
                    {'trigger_onset'}, ...
                    absTrigSchedule(k) ...
                    );

                % Add a trigger to the PsychPortAudio Schedule if there are
                % any more left to add
                if k + bufferSize <= numel(absTrigSchedule)
                    addToScheduleWrapper(k + bufferSize);
                end

                % Handle keyboard input
                numEventsAvail = KbEventAvail();
                while numEventsAvail > 0
                    [event, numEventsAvail] = KbEventGet();
                    if event.Pressed && event.Keycode == quitKey
                        endTestEarly = true;
                        [~, ~, ~, endTime] = PsychPortAudio( ...
                            'Stop', ...
                            pahandle ...
                            );
                        break
                    end
                end
                if endTestEarly
                    break
                end
            end
            if ~endTestEarly
                % Wait until last trigger is sent
                [~, ~, ~, endTime] = PsychPortAudio('Stop', pahandle, 3);
            end
            msg = "Test ended after ~" + (endTime - startTime) + "s.";
            obj.log.print(msg, 2);

            % Stop recording on LabRecorder if applicable
            if recordData
                obj.log.print("Stopping recording on LabRecorder", 2);
                pause(0.5);
                writeline(lr, 'stop');
                pause(1);
            end

            % Determine if test ended early
            endedEarly = endTestEarly;
            % Determine if the test ran successfully
            result = (~endedEarly) && (k == numel(absTrigSchedule));
        end

        function atEndOfSession(obj)
            arguments
                obj
            end
            % TODO: should we also stop recording on LR?

            PsychPortAudio('Close');
            KbQueueRelease();

            atEndOfSession@SyncSession(obj);
        end
    end
end