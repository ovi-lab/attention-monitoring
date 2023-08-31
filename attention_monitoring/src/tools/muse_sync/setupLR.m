function lr = setupLR(root, template, nvargs)
    % Setup LabRecorder. LabRecorder must already be running.

    arguments
        root
        template
        nvargs.tcpAddress = 'localhost'
        nvargs.tcpPort = 22345
        nvargs.verbose (1,1) {mustBeInteger} = 0
    end

    tcpAddress = nvargs.tcpAddress;
    tcpPort = nvargs.tcpPort;
    log = Logger(nvargs.verbose, "setupLR");

    try
        lr = tcpclient(tcpAddress, tcpPort);
    catch ME
        if strcmp(ME.identifier, 'MATLAB:networklib:tcpclient:cannotCreateObject')
            log.print( ...
                "Could not connect to LabRecorder. " + ...
                "Perhaps it is not yet running?", ...
                1, ...
                "labelSuffix", "-ERROR" ...
                );
        end
        rethrow(ME);
    end

    options = [
        "root", root;
        "template", template;
        ];
    command = ['filename', char(sprintf(' {%s:%s}', options'))];
    writeline(lr, command);
    writeline(lr, 'update');
    writeline(lr, 'select all');
end