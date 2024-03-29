
% log = Logger(3, "museSync");
% 
% recordingFile = runSyncSession( ...
%     fullfile(pwd(), "sync_session_data"), ...
%     verbose=log.verbose, ...
%     autoRecord=true, ...
%     recordingLength=20, ...
%     recordingName="tenMinBluemuseDoubleSR" ...
%     );
% 
% if ~strcmp(recordingFile, "")
%     log.print("Muse synchronisation session recording file: ", 2);
%     log.print(recordingFile, 2, "literal", true);
% else
%     log.print("No Muse synchronisation session recording file.", 2);
% end
% 
% vis = SyncSessionVisualizer(recordingFile, verbose=log.verbose);


ms = SyncPPG(fullfile(pwd, "sync_session_data"), verbose=3);