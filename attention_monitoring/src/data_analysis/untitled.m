dataPath1 = "C:\Users\HP User\source\repos\attention-monitoring\src\data\gradCPT_sessions\S11_130723_P0\s11_130723_p0_full_block_1_data.xdf";
dataPath2 = "C:\Users\HP User\source\repos\attention-monitoring\src\data\gradCPT_sessions\S11_130723_P0\s11_130723_p0_full_block_2_data.xdf";
[data, header] = load_xdf(dataPath1);

dataStreams = dictionary;
markerStreams = dictionary;
for k = 1:numel(data)
    streamType = data{k}.info.type;
    streamName = data{k}.info.name;
    if any(strcmp(["EEG", "PPG", "Accelerometer", "Gyroscope"], streamType))
        dataStreams(streamType) = data{k};
    else
        markerStreams(streamName) = data{k};
    end
end

fig = figure;
ax = gca;

eeg = dataStreams('EEG');
stimMarkers = markerStreams('stimuli_marker_stream');
responseMarkers = markerStreams('response_marker_stream');

gap = 0.1;

hold on;
% plot average eeg
x = eeg.time_stamps;
y = mean(eeg.time_series, 1);
plot(ax, x - x(1), y - mean(y));
% plot stimuli markers
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'transition_period_start'));
y = ones(1,length(x));
plot(ax, x - x(1), y, 'b.');
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'static_period_start'));
y = ones(1,length(x));
plot(ax, x - x(1), y, 'g.');
x = responseMarkers.time_stamps(strcmp(responseMarkers.time_series, 'response'));
y = ones(1,length(x));
plot(ax, x - x(1), y, 'r|');
hold off;

