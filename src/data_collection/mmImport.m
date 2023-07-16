function [museData, museElements] = mmImport(fileName)
%Mind Monitor Import by James Clutterbuck [https://Mind-Monitor.com]
%Usage Example: [museData, museElements] = mmImport('mindMonitor_2019-05-25.csv')

varNames = {'TimeStamp','Delta_TP9','Delta_AF7','Delta_AF8','Delta_TP10','Theta_TP9','Theta_AF7','Theta_AF8','Theta_TP10','Alpha_TP9','Alpha_AF7','Alpha_AF8','Alpha_TP10','Beta_TP9','Beta_AF7','Beta_AF8','Beta_TP10','Gamma_TP9','Gamma_AF7','Gamma_AF8','Gamma_TP10','RAW_TP9','RAW_AF7','RAW_AF8','RAW_TP10','AUX_RIGHT','Accelerometer_X','Accelerometer_Y','Accelerometer_Z','Gyro_X','Gyro_Y','Gyro_Z','HeadBandOn','HSI_TP9','HSI_AF7','HSI_AF8','HSI_TP10','Battery','Elements'};
varTypes = {'char','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','double','char'};
varNamesWaves = {'TimeStamp','Delta_TP9','Delta_AF7','Delta_AF8','Delta_TP10','Theta_TP9','Theta_AF7','Theta_AF8','Theta_TP10','Alpha_TP9','Alpha_AF7','Alpha_AF8','Alpha_TP10','Beta_TP9','Beta_AF7','Beta_AF8','Beta_TP10','Gamma_TP9','Gamma_AF7','Gamma_AF8','Gamma_TP10','RAW_TP9','RAW_AF7','RAW_AF8','RAW_TP10','AUX_RIGHT','Accelerometer_X','Accelerometer_Y','Accelerometer_Z','Gyro_X','Gyro_Y','Gyro_Z','HeadBandOn','HSI_TP9','HSI_AF7','HSI_AF8','HSI_TP10','Battery'};
varNamesElements = {'TimeStamp','Elements'};

opts = delimitedTextImportOptions('VariableNames',varNames,...
    'SelectedVariableNames',varNamesWaves,...
    'VariableTypes',varTypes,...
    'Delimiter',',',...
    'DataLines',[2,inf],...
    'EmptyLineRule','skip',...
    'MissingRule','omitrow',...
    'ImportErrorRule','omitrow',...
    'ExtraColumnsRule','ignore');
opts.VariableNamesLine=1;
%Brain wave data with no elements (Blink, Jaw_Clench, Markers)
museData = readtable(fileName,opts);
museData.TimeStamp = datetime(datevec(museData.TimeStamp),'Format','yyyy-MM-dd HH:mm:s.SSS');

%Elements with no brain wave data
opts.SelectedVariableNames = varNamesElements;
% museElements = readtable(fileName,opts);
% museElements.TimeStamp = datetime(datevec(museElements.TimeStamp),'Format','yyyy-MM-dd HH:mm:s.SSS');
museElements = nan(1);

clear fileName; clear varNames;clear varTypes;clear varNamesWaves;clear varNamesElements; clear opts;
end