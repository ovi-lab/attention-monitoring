classdef SyncSessionVisualizer
    % TODO: validate that response time is correct
    properties (SetAccess = private)
        recordingFile (1,:) string  % Path to xdf file containing syncSession data
        streams struct = struct     % Contains the relevant streams obtained from `recordingFile`
        startTime (1,1) double = 0  % The timestamp in the streams that is used as time = 0 for processed data
        data struct = struct        % Contains processed data
    end
    properties (Access = private, Hidden)
        log Logger
        numPPGchannels (1,1) {mustBeInteger} = 1
    end

    methods
        function obj = SyncSessionVisualizer(recordingFile, nvargs)
            arguments
                recordingFile (1,:) string {mustBeFile}
                nvargs.verbose = 0
            end

            obj.recordingFile = recordingFile;

            obj.log = Logger(nvargs.verbose, "SyncSessionVisualizer");

            obj.log.print("Creating the visualizer.", 3);
            
            obj.log.print("Loading session data...", 2);
            [data, ~] = load_xdf(obj.recordingFile, ...
                'CorrectStreamLags', false, ...
                'Verbose', false ...
                );
            obj.log.print("Loaded session data.", 2);
            
            % Get the desired streams
            for k = 1:numel(data)
                streamType = data{k}.info.type;
                streamName = data{k}.info.name;
                if strcmp(streamType, "PPG")
                    obj.streams.(streamType) = data{k};
                elseif strcmp(streamName, "museSync_markers")
                    obj.streams.(streamName) = data{k};
                end
            end

            % TODO: Fix this
            msg1 = ["No PPG data found. ", "No marker data found. "];
%             msg2 = ["Will plot markers only.", "Will plot PPG data only."];
            dataExists = isfield(obj.streams, ["PPG", "museSync_markers"]);
%             msg = msg1(~dataExists) + msg2(dataExists & ~flip(dataExists));
            if any(~dataExists)
                obj.log.print(msg1(~dataExists), 2);
            end

            % Extract values necessary for plotting
            if isfield(obj.streams, "PPG")
                obj.startTime = min(obj.streams.PPG.time_stamps(:,1));
                obj.numPPGchannels = 3;
            end

            % Process the raw data. Do this for each channel PPG channel
            % and the marker stream, if they exist.
            for k = 1:obj.numPPGchannels
                % Create a `struct` to store data for this PPG channel
                chnl = struct;

                % Get the name for this channel. If there was no PPG data,
                % treat it as a "marker channel".
                if isfield(obj.streams, "PPG")
                    channel = obj.streams.PPG.info.desc.channels ...
                        .channel{k}.label;
                else
                    channel = "markers_only";
                end

                % Extract relevant PPG data if it exists
                if isfield(obj.streams, "PPG")
                    % Get PPG data with timestamps rereferenced to
                    % obj.startTime
                    x = obj.streams.PPG.time_stamps;
                    x = x - obj.startTime;
                    y = obj.streams.PPG.time_series(k,:);
                    % Center signal vertically on the x axis
                    y = y - mean(y); 
                    % Normalise signal
                    y = y ./ max(y);

                    if ~issorted(x)
                        msg = "PPG timestamps are not in ascending " + ...
                            "order for channel """ + channel + """, " + ...
                            "which may have unintended consequences.";
                        obj.log.print(msg, 1, labelSuffix="-WARNING");
                    end
                    
                    chnl.ppg = struct;
                    chnl.ppg.timeStamps = x;
                    chnl.ppg.values = y;
                end

                % Extract relevant marker data if it exists
                if isfield(obj.streams, "museSync_markers")
                    % Get timestamps of screen colour changes rereferenced
                    % to obj.startTime
                    x = obj.streams.museSync_markers.time_stamps;
                    x = x - obj.startTime;
                    % Ensure timestamps are in ascending order
                    x = sort(x);

                    chnl.responseTimes = struct;
                    chnl.responseTimes.timeStamps = x;
                end

                % Determine the response times of the PPG data to each
                % marker (if possible)
                if all(isfield(obj.streams, ["PPG", "museSync_markers"]))
                    % The time of the first x-intercept of the PPG data
                    % after each screen colour change marker is considered
                    % the time-of-response corresponding to that marker
                    x = chnl.ppg.timeStamps;
                    y = chnl.ppg.values;
                    markerTimes = chnl.responseTimes.timeStamps;
                    % signum(signal): will result in peaks in dy/dx when
                    % signal is close to 0 (ie. near the x intercepts)
                    y = sign(y);
                    % Replace all zero values with the next non-zero value
                    % (or negative of previous non-zero value if
                    % unavailable) so that dy/dx has distinct peaks
                    for kk = find(y == 0)
                        index = find((y ~= 0 & x > x(kk)), 1, 'first');
                        if lennth(index) ~= 0
                            y(kk) = y(index);
                        else
                            msg = "Possible error while trying to " + ...
                                "calculate response times for " + ...
                                "channel """ + channel + """: Unable" + ...
                                "to replace 0 value at index" + kk + ...
                                " as no later non-zero values were " + ...
                                "found. It will instead be replaced " + ...
                                "by the negative of the last non-" + ...
                                "zero value.";
                            obj.log.print( ...
                                msg, 1, ...
                                "labelPrefix", "-WARNING" ...
                                );
                            index = find((y ~= 0 & x < x(kk)), 1, 'last');
                            if len(index) ~= 0
                                y(kk) = -1 * y(index);
                            else
                                msg = "No previous non-zero values " + ...
                                    "found. Value at index " + kk + ...
                                    "will be kept as 0.";
                                obj.log.print( ...
                                    msg, 1, ...
                                    "labelPrefix", "-WARNING" ...
                                    );
                            end
                        end
                    end
                    % Approx dy/dx: dy(n) = (y(n+1) - y(n)) ...
                    %                       / (x(n+1) - x(n))
                    dy = diff(y)./diff(x);
                    dy(end + 1) = 0;
                    % Find the first x-intercept after each marker. The
                    % same x-intercept cannot be used for different markers
                    responseTimes = zeros(size(markerTimes));
                    ppgVals = chnl.ppg.values;
                    lastIndex = 0;
                    for kk = 1:numel(markerTimes)
                        % Find index of the first time stamp after this 
                        % marker where dy/dx is non-zero (-> approximate 
                        % x-intercept). Do not re-use indices.
                        mask = (dy ~= 0) & (x >= markerTimes(kk));
                        if lastIndex > 0
                            mask = mask & (x > x(lastIndex));
                        end
                        index = find(mask, 1);
                        % x-intercept is located sometime between the time
                        % stamp at this index (if it exists) and the next
                        % one that has a different sign in the PPG data.
                        % If the end of the timestamps is reached before
                        % finding a suitable next timestamp, specify no
                        % response time.
                        foundResponseTime = false;
                        if ~isempty(index)
                            p = 1;
                            while ( ...
                                    index + p <= numel(ppgVals) ...
                                    && sign(ppgVals(index)) == ... 
                                        sign(ppgVals(index + p)) ...
                                    )
                                p = p + 1;
                            end
                            if index + p <= numel(ppgVals)
                                xInt = interp1( ...
                                    double(ppgVals(index + [0,p])), ...
                                    double(x(index + [0,p])), ...
                                    0 ...
                                    );
                                % The response time is calculated as the
                                % difference between the time-of-response
                                % (that is, the time of the above
                                % x-intercept, `xInt`) and the time stamp
                                % of the corresponding marker
                                responseTimes(kk) = xInt - markerTimes(kk);
                                lastIndex = index;
                                foundResponseTime = true;
                            end
                        end
                        if ~foundResponseTime
                            responseTimes(kk) = nan;
                        end
                    end
                    chnl.responseTimes.values = responseTimes;
                end
                
                % Save the `struct` for this channel as a property of
                % `obj.data`. 
                obj.data.(channel) = chnl;
            end
        end

        function plotFull(obj, channels, filtargs)
        % Create a plot for each of the specified channels consisting of:
        %  - (if PPG data exists) Average-referenced and normalized PPG
        %    data VS time since `obj.startTime` in seconds.
        %  - (if marker data exists) Markers showing the time(s) since
        %    `obj.startTime` in seconds that the PPG signal was triggered
        %    (ie. when Psychtoolbox caused the screen to change colour).
        %    Markers are labelled with the time in milliseconds that the
        %    PPG signal took to respond to that marker if available, 
        %    otherwise they are labelled with that marker's timestamp.
        %  - (if PPG and marker data exist) Grey regions showing the 
        %    duration of the PPG response time(s) to each marker.
        % Specify desired channels as strings containing the name of the
        % corresponding channel in `obj.data`. Specifying invalid names
        % throws an error. If no names are specified, all available
        % channels are used.
        %
        % Note that all above data are subject to error and are only
        % estimates of true values.
            arguments
                obj
            end
            arguments (Repeating)
                channels (:,1) string
            end
            arguments
                filtargs.domain (2,1) double = [-inf, inf];
            end

            % Get a filter for processing data before plotting
            filtargsCell = namedargs2cell(filtargs);
            filt = obj.makeFilt(filtargsCell{:});
                  
            % Validate the specified channels
            channels_ = reshape(string(channels), [], 1);
            if numel(channels_) == 0
                validChannels = string(fieldnames(obj.data));
            elseif any(~isfield(obj.data, channels_))
                invalidChannels = channels_(~isfield(obj.data, channels_));
                ME = MException( ...
                    "MATLAB:nonExistentField", ...
                    "Invalid channel name(s): " + ...
                    join(invalidChannels, ", ") ...
                    );
                throw(ME);
            else
                validChannels = channels_;
            end

            % Plot the data
            figure;
            t = tiledlayout(numel(validChannels), 1);

            % Preallocate arrays to store the axes of the plots
            ax = gobjects(numel(validChannels), 1);
            ax2 = gobjects(numel(validChannels), 1);

            % Plot each specified channel
            for k = 1:numel(validChannels)
                chnl = obj.data.(validChannels(k));
                
                ax(k) = nexttile;
                hold on;
                ax(k).YLim = [-1,1];
                ax(k).XLim = [-inf,inf];
                ylabel(ax(k), validChannels(k));

                % Determine which data exists;
                ppgExists = isfield(chnl, "ppg");
                markerTimesExist = all( ...-
                    isfield(chnl, "responseTimes"), ...
                    isfield(chnl.responseTimes, "timeStamps") ...
                    );
                responseTimesExist = all( ...
                    isfield(chnl, "responseTimes"), ...
                    isfield(chnl.responseTimes, "values") ...
                    );

                % Plot ppg data if available
                if ppgExists
                    [timeStamps, values] = filt( ...
                        chnl.ppg.timeStamps, ...
                        chnl.ppg.values ...
                        );
                    plot(ax(k), timeStamps, values, "b");
                    % Plot a "x axis" for the PPG channel
                    yline(ax(k), 0);
                else
                    msg = "PPG data not found for channel " + ...
                        validChannels(k);
                    obj.log.print(msg, 2);
                end

                % Plot marker data if available
                if markerTimesExist
                    [timeStamps, ~] = filt( ...
                        chnl.responseTimes.timeStamps, ...
                        nan(size(chnl.responseTimes.timeStamps)) ...
                        );
                    % Plot a vertical line at time stamp of every marker
                    if ~isempty(timeStamps)
                        xline(ax(k), timeStamps, "r");
                    end
                    % Specify marker labels as the marker time stamp
                    labels = compose("%.4f", timeStamps);
                    labelsTitle = "Time of PPG Trigger (s)";

                    % Plot response time data if available
                    if responseTimesExist
                        [~, values] = filt( ...
                            chnl.responseTimes.timeStamps, ...
                            chnl.responseTimes.values ...
                            );
                        % For each marker, shade in region from marker time
                        % to time of PPG response (if available)
                        for kk = 1:numel(timeStamps)
                            if ~isnan(values(kk))
                                pos = [
                                    timeStamps(kk), ...
                                    ax(k).YLim(1), ...
                                    values(kk), ...
                                    ax(k).YLim(2) - ax(k).YLim(1) ...
                                    ];
                                plt = rectangle( ...
                                    ax(k), ...
                                    'Position', pos, ...
                                    'FaceColor', '#DADADA', ...
                                    'EdgeColor', 'none' ...
                                    );
                                uistack(plt, 'bottom');
                            end
                        end
                        % Change marker labels to show the PPG response
                        % time corresponding to that marker.
                        labels = compose("%.1f", values * 1000);
                        labels(isnan(values)) = "N/A";
                        labelsTitle = "PPG Response Time (ms)";
                    else
                        msg = "Response time data not found for " + ...
                            "channel " + validChannels(k);
                        obj.log.print(msg, 2);
                    end

                    % Label the markers
                    ax2(k) = axes(t);
                    ax2(k).Layout.Tile = k;
                    ax2(k).Color = "none";
                    ax2(k).Box = 'off';
                    ax2(k).YAxis.Visible = "off";
                    ax2(k).XAxisLocation = 'top';
                    ax2(k).XAxis.Color = "none";
                    ax2(k).XAxis.TickValues = timeStamps;
                    ax2(k).XAxis.TickLabels = labels;
                    ax2(k).XAxis.TickLabelColor = "r";
                    linkaxes([ax(k), ax2(k)]);
                    uistack(ax2(k), 'bottom');
                    % Only show the marker labels on the top chart
                    if k == 1 && ~isempty(timeStamps)
                        xlabel(ax2(k), labelsTitle, "Color", "r");
                        ax2(k).XAxis.LabelHorizontalAlignment = "left";
                    end

                else
                    msg = "Marker data not found for channel " + ...
                        validChannels(k);
                    obj.log.print(msg, 2);
                end

                % Only show the x axis labels on the bottom chart 
                if k ~= numel(validChannels)
                    ax(k).XAxis.TickLabels = {''};
                end
                
                hold off;
            end

            linkaxes(ax);
            t.TileSpacing = "tight";
            xlabel(t, "Time (s)");
            ylabel(t, "Normalised PPG Amplitude");
            title(t, "Muse Time-Synchronisation Results");
        end

        function plotResponseTimes(obj, channels, filtargs)
            arguments
                obj
            end
            arguments (Repeating)
                channels (:,1) string
            end
            arguments
                filtargs.domain (2,1) double = [-inf, inf];
            end

            % Get a filter for processing data before plotting
            filtargsCell = namedargs2cell(filtargs);
            filt = obj.makeFilt(filtargsCell{:});
                  
            % Validate the specified channels
            channels_ = reshape(string(channels), [], 1);
            if numel(channels_) == 0
                validChannels = string(fieldnames(obj.data));
            elseif any(~isfield(obj.data, channels_))
                invalidChannels = channels_(~isfield(obj.data, channels_));
                ME = MException( ...
                    "MATLAB:nonExistentField", ...
                    "Invalid channel name(s): " + ...
                    join(invalidChannels, ", ") ...
                    );
                throw(ME);
            else
                validChannels = channels_;
            end

            % Plot the data
            figure;
            t = tiledlayout(numel(validChannels), 1);

            % Preallocate array to store the axes of the plots
            ax = gobjects(numel(validChannels), 1);

            % Plot each specified channel
            for k = 1:numel(validChannels)
                chnl = obj.data.(validChannels(k));
                
                ax(k) = nexttile;
                ylabel(ax(k), validChannels(k));
                
                % Plot response times as a function of time, if they exist
                responseTimesExist = all([ ...
                    isfield(chnl, "responseTimes"), ...
                    isfield(chnl.responseTimes, "timeStamps"), ...
                    isfield(chnl.responseTimes, "values") ...
                    ]);
                if responseTimesExist
                    [timeStamps, values] = filt( ...
                        chnl.responseTimes.timeStamps, ...
                        chnl.responseTimes.values ...
                        );
                    plot(ax(k), timeStamps, values * 1000, "b");
                else
                    msg = "Response time data not found for channel " + ...
                        validChannels(k);
                    obj.log.print(msg, 2);
                end

                % Only show the x axis labels on the bottom chart 
                if k ~= numel(validChannels)
                    ax(k).XAxis.TickLabels = {''};
                end
            end

            linkaxes(ax);
            t.TileSpacing = "tight";
            xlabel(t, "Time (s)");
            ylabel(t, "Response Time (ms)");
            title( ...
                t, ...
                "Muse Response Time", ...
                "Calculated using PPG with Color Triggers" ...
                );
        end
    end

    methods (Access = private, Hidden)
        function filt = makeFilt(obj, nvargs)
            % Make a helper function for filtering data before plotting.
            arguments
                obj
                nvargs.domain (2,1) double = [-inf, inf];
            end

            filt = @filt_;
            function [newTimes, newVals] = filt_(oldTimes, oldVals)
                % Limit data to the specified domain
                domainMask = oldTimes >= nvargs.domain(1) ...
                    & oldTimes <= nvargs.domain(2);
                newTimes = oldTimes(domainMask);
                newVals = oldVals(domainMask);
            end
        end
    end
end