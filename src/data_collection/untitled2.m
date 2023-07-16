%% 1

trimmedLength = minutes(5);
FS = 128;
meditation = [
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\m1.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\m2.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\m3.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\m4.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\m5.csv"
    ];

baseline = [
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\w1.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\w2.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\w3.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\w4.csv", ...
    "C:\Users\HP User\Documents\HCI Lab\muse recordings\data\w5.csv"
    ];

files = baseline;

datas = cell(1,numel(files));
for k = 1:numel(files)
    % import file
    [data, elements] = mmImport(files(k));
    data = table2timetable(data);
    % average band signals across all electrodes
    data = meanBands(data);
    % rereference time vector to start at 0
    data.Time = data.Time - data.Time(1);
    %resample data
    data = retime(data, 'regular', 'nearest', 'SampleRate', FS);
    % trim to preset time length, with the selected time range near the
    % middle of the original signal
    targetRange = data.Time(end)/2 + [-0.5, 0.5]*trimmedLength;
    data = data(timerange(targetRange(1), targetRange(2)), :);
    % rereference time vector to start at 0
    data.Time = data.Time - data.Time(1);
        
    datas{k} = data;
end

backup = datas;

%% 2

datas = datasM;

% synchronize and average across sessions
template = datas{1};
values = zeros(height(template), width(template), numel(datas));
vars = template.Properties.VariableNames;
for k = 1:numel(datas)
    assert(all(strcmp(vars, template.Properties.VariableNames)));
    values(:,:,k) = table2array(datas{k});
end
values = mean(values, 3);
T = array2timetable(values, 'RowTimes', template.Time, 'VariableNames', vars);

fig = figure();
ax = gca;
data = T;
data = smoothdata(data);
hold on;
for k = 1:numel(data.Properties.VariableNames)
    plot(ax, data, data.Properties.VariableNames{k}, ...
        LineWidth=1 ...
        );
end
hold off;
legend(ax, 'Orientation', 'horizontal', 'Location', 'best');
ylim(ax, [0,1]);

fig.WindowStyle = 'normal';
fig.Resize = 'off';
fig.Units = "centimeters";
fig.Position = [0,0,1,0.5] * 30;
fig.Units = "normalized";




%     values = zeros(height(ttables{1}), width(ttables{1}, numel(ttables)));
%     vars = ttables{1}.Properties.VariableNames;
%     for k = 1:numel(ttables)
%         assert(all(strcmp(vars, ttables(k).Properties.VariableNames)));
%         values(:,:,k) = table2array(ttables{k});
%     end
%     values = mean(values, 3);
% 
%     T = timetable(values, 'RowTimes', template.Time, 'VariableNames', vars);


%% 3


function T = meanBands(data)
    bands = ["Alpha", "Beta", "Gamma", "Delta", "Theta"];
    T = timetable(data.TimeStamp);
    for k = 1:length(bands)
        bandValues = data(:, bands(k) + wildcardPattern);
        vars = bandValues.Properties.VariableNames;
        disp(bands(k) + ": " + strjoin(vars, ","));
        T = addvars(T, mean(bandValues{:,:}, 2), 'NewVariableNames', bands(k)); 
    end
end

function mmPlotAve(museData)
    hold on;
    plot(museData.TimeStamp, (museData.Delta_TP9+museData.Delta_AF7+museData.Delta_AF8+museData.Delta_TP10)/4,'Color','#CC0000');
    plot(museData.TimeStamp, (museData.Theta_TP9+museData.Theta_AF7+museData.Theta_AF8+museData.Theta_TP10)/4, 'Color','#9933CC');
    plot(museData.TimeStamp, (museData.Alpha_TP9+museData.Alpha_AF7+museData.Alpha_AF8+museData.Alpha_TP10)/4, 'Color','#0099CC');
    plot(museData.TimeStamp, (museData.Beta_TP9+museData.Beta_AF7+museData.Beta_AF8+museData.Beta_TP10)/4, 'Color','#669900');
    plot(museData.TimeStamp, (museData.Gamma_TP9+museData.Gamma_AF7+museData.Gamma_AF8+museData.Gamma_TP10)/4, 'Color','#FF8A00');
    title('Mind Monitor - Absolute Brain Waves');
    hold off;
end