classdef (Abstract) SyncSession
    % Properties
    properties (SetAccess = protected)
        dataDir (1,:) string {mustBeTextScalar} = pwd
        recordingName (1,:) string {mustBeTextScalar} ...
            = "muse_sync_data.xdf"
        recordingFile (1,:) string {mustBeTextScalar} ...
            = fullfile(pwd, "muse_sync_data.xdf")
    end

    properties (Dependent)
        vis
    end

    properties (Access = protected, Hidden)
        log Logger
        visObj = []
    end

    properties (Access = private, Hidden)
        markerOutlet
        lr
    end

    % Methods
    methods
        function obj = SyncSession(dataDir, nvargs)
            arguments
                dataDir = pwd()
                nvargs.recordingName = "muse_sync_data.xdf"
                nvargs.verbose = 0
            end

            obj.dataDir = dataDir;
            obj.recordingName = nvargs.recordingName;
            
            obj.log = Logger(nvargs.verbose, class(obj));

            % Get the path to the file that will store the recording data.
            [~, baseFileName, ~] = fileparts(obj.recordingName);
            template = baseFileName + ".xdf";
            k = 1;
            while isfile(fullfile(dataDir, template))
                template = baseFileName + "_" + k + ".xdf";
                k = k + 1;
            end
            obj.recordingFile = fullfile(dataDir, template);
            if k ~= 1
                msg = "Specified recording file already exists, " + ...
                    "will instead use the specified recording file " + ...
                    "with number appended to the end of its name.\n ";
                obj.log.print(msg, 2);
                msg = "Specified recording file path: " + ...
                    fullfile(dataDir, baseFileName + ".xdf");
                obj.log.print(msg, 2, "literal", true, "wrapText", false);
            end
            msg = "Selected recording file path: " + obj.recordingFile;
            obj.log.print(msg, 2, "literal", true, "wrapText", false);
        end

        function value = get.vis(obj)
            % Return the `SyncSessionVisualizer` object for this session if
            % the recording exists (indicating the session has already been
            % run), otherwise return an empty array as a placeholder.
            value = [];
            if isfile(obj.recordingFile)
                if isempty(obj.visObj)
                    obj.visObj = SyncSessionVisualizer( ...
                        obj.recordingFile, ...
                        "verbose", obj.log.verbose ...
                        );
                end
                value = obj.visObj;
            end
        end
    end

    methods (Sealed)
        function result = run(obj, nvargs)
            % Run the muse synchronization session and record data. Returns
            % true iff the entire procedure was successfully performed,
            % meaning that the procedure ran for the required length of
            % time and did not end early, data was successfully recorded to
            % `obj.recordingFile`, no unhandled errors occurred, etc. Note
            % that result == false does not imply that a recording file was
            % not created, just that if the recording file exists, it may
            % not be complete or correct.
            arguments
                obj
                nvargs.recordData (1,1) logical = true
                nvargs.autoStart (1,1) logical = true
                nvargs.recordingLength (1,1) double = 10
            end

            if isfile(obj.recordingFile)
                ME = MException( ...
                    "SyncSession:recordingAlreadyExists", ...
                    "The recording file already exists." ...
                    );
                throw(ME);
            end

            obj.log.print("Running the synchronization session.", 2);

            try
                % Setup the LSL Stream for sending markers
                obj.log.print("Setting up the LSL Stream.", 2);
                lib = lsl_loadlib();
                streamInfo = lsl_streaminfo( ...
                    lib, ...
                    'museSync_markers', ...
                    'Markers', ...
                    1, 0, ...
                    'cf_string' ...
                    );
                obj.markerOutlet = lsl_outlet(streamInfo);
    
                % Setup LabRecorder
                if nvargs.recordData
                    [~, fileName, ext] = fileparts(obj.recordingFile);
                    obj.lr = setupLR( ...
                        obj.dataDir, ...
                        fileName + ext, ...
                        "verbose", obj.log.verbose ...
                        );
                end

                % Run the session
                obj.log.print("Performing the test", 2);
                [result, endedEarly] = obj.runProcedure( ...
                    obj.markerOutlet, ...
                    obj.lr, ...
                    nvargs.recordData, ...
                    nvargs.autoStart, ...
                    nvargs.recordingLength ...
                    );

            catch ME
                % Fail gracefully if there are any errors 
                try
                    obj.endSession('error');
                catch ME2
                    msg = "An error occured while trying to perform " + ...
                        "end-of-session operations. This error may " + ...
                        "be a result of the original error that " + ...
                        "caused the session to end. The error " + ...
                        "stacktrace is:\n";
                    obj.log.print(msg, "labelSuffix", "-ERROR");
                    disp(getReport(ME2));
                    msg = "\n-- End of stacktrace --\n\n";
                    obj.log.print(msg, "labelSuffix", "-ERROR");
                end
                rethrow(ME);
            end

            if endedEarly
                obj.endSession('early');
            else
                obj.endSession();
            end
        end
    end

    methods (Access = private, Sealed, Hidden)
        function endSession(obj, type, printout)
            % Executes at the end (successful or not) of a session,
            % performing necessary operations for ending gracefully.
            % Subclasses should NOT override this method, instead see
            % `atEndOfSession`.
            arguments
                obj
                type {mustBeMember(type,["normal","early","error"])} ...
                    = "normal"
                printout {mustBeText} = ''
            end
            if any(strcmp(type, {'early', 'error'}))
                obj.log.print("\n== ENDING SESSION EARLY ==\n\n", 1);
            end
            if strcmp(type, 'error')
                msg = "The session has ended due to an error. " + ...
                    "Attempting to end the session gracefully...";
                obj.log.print(msg, 1, "labelSuffix", "-ERROR");
            end
        
            if ~strcmp(printout, '')
                disp(printout);
            end
        
            msg = "Attempting to perform end-of-session operations...";
            obj.log.print(msg, 2)
            try
                obj.atEndOfSession();
            catch ME
                rethrow(ME)
            end
            msg = "Successfully performed end-of-session operations.";
            obj.log.print(msg, 2);
        end
    end

    methods (Access = protected, Hidden)
        function atEndOfSession(obj)
            % Performs necessary operations for ending gracefully. This
            % method is called internally by `obj.endSession`, see
            % definition of that function for expected use. If a subclass
            % overrides this method, the subclass method must call the
            % superclass method.
            arguments
                obj
            end
            if ~isempty(obj.markerOutlet)
                obj.log.print("Closing the LSL marker stream...", 3);
                obj.markerOutlet.delete();
            end
            if ~isempty(obj.lr)
                obj.log.print("Stopping recording on LabRecorder...", 3);
                writeline(obj.lr, 'stop');
            end
        end
    end

    methods (Access = protected, Hidden, Abstract)
        [result, endedEarly] = runProcedure( ...
                obj, markerOutlet, lr, recordData, autoStart, ...
                recordingLength ...
                )
        % Runs the procedure for the subclass of SyncSession. This is
        % called internally when the user calls `obj.run`, see the
        % definition for that function for expected use.
        %
        % MarkerOutlet (1,1) lsl_outlet
        %   The LSL stream outlet to send marker data to
        % lr (1,1) tcpclient
        %   The TCP/IP object associated with LabRecorder
        % recordData (1,1) logical
        %   Whether to make a recording on LabRecorder
        % autoStart (1,1) logical
        %   Whether to automatically start the test and begin recording on
        %   LabRecorder (if applicable). If false, wait for user input to
        %   start.
        % recordingLength (1,1) double
        %   The desired length of the recording in seconds
        %
        % result (1,1) logical
        %   True iff the entire procedure was successfully performed,
        %   meaning that the procedure ran for the required length of time
        %   and did not end early, data was successfully recorded to
        %   `obj.recordingFile` (applies iff `recordData`==true), no
        %   unhandled errors occurred, etc.
        % endedEarly (1,1) logical
        %   True iff the session was ended early.
    end
end