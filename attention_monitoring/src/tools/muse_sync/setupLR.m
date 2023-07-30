function lr = setupLR(root, template, tcpAddress, tcpPort)
    % Setup LabRecorder. LabRecorder must already be running.

    arguments
        root
        template
        tcpAddress = 'localhost'
        tcpPort = 22345
    end

    try
        lr = tcpclient(tcpAddress, tcpPort);
    catch ME
        if strcmp(ME.identifier, 'MATLAB:networklib:tcpclient:cannotCreateObject')
            disp( ...
                "Could not connect to LabRecorder." + ...
                "Perhaps it is not yet running?" ...
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