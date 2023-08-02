dataPath1 = "C:\Users\HP User\source\repos\attention-monitoring\attention_monitoring\src\data\gradCPT_sessions\S68_180723_Ptiaan\s68_180723_ptiaan_full_block_1_data.xdf";
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

xStart = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'block_start'));
xStart = xStart(1);
gap = 0.1;

hold on;
% plot average eeg
x = eeg.time_stamps;
y = mean(eeg.time_series, 1);
plot(ax, x - xStart, y - mean(y));
% plot stimuli markers
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'transition_period_start'));
y = ones(1,length(x));
plot(ax, x - xStart, y, 'b|', MarkerSize=10);
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'static_period_start'));
y = ones(1,length(x));
plot(ax, x - xStart, y, 'g|', MarkerSize=10);
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'block_start'));
y = ones(1,length(x));
plot(ax, x - xStart, y, 'm|', MarkerSize=10);
x = stimMarkers.time_stamps(strcmp(stimMarkers.time_series, 'block_stop'));
y = ones(1,length(x));
plot(ax, x - xStart, y, 'm|', MarkerSize=10);
% plot response markers
x = responseMarkers.time_stamps(strcmp(responseMarkers.time_series, 'response'));
y = ones(1,length(x));
plot(ax, x - xStart, y, 'r.', MarkerSize=10);
hold off;

