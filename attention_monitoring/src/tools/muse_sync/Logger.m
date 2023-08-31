% TODO: dont r=print label if line is empty
% implement gap in formatText

classdef Logger
    properties
        verbose (1,1) {mustBeInteger} = 0
        label (1,:) string {mustBeTextScalar} = ""
        lineWidth (1,1) {mustBeInteger, mustBeNonnegative} = 80
        baseIndentLevel (1,1) {mustBeInteger, mustBeNonnegative} = 0
        indentSize (1,1) {mustBeInteger, mustBeNonnegative} = 4
        labelDelimiter (1,:) string {mustBeTextScalar} = ":"
        labelTextGapSize (1,1) {mustBeInteger, mustBeNonnegative} = 1
    end

    methods
        function obj = Logger(verbose, label, nvargs)
            arguments
                verbose = 0
                label = ""
                nvargs.lineWidth = 80
                nvargs.baseIndentLevel = 0
                nvargs.indentSize = 4
                nvargs.labelDelimiter = ":"
                nvargs.labelTextGapSize = 1
            end

            obj.verbose = verbose;
            obj.label = label;
            obj.lineWidth = nvargs.lineWidth;
            obj.baseIndentLevel = nvargs.baseIndentLevel;
            obj.indentSize = nvargs.indentSize;
            obj.labelDelimiter = nvargs.labelDelimiter;
            obj.labelTextGapSize = nvargs.labelTextGapSize;
        end

        function print(obj, msg, verboseLevel, nvargs_formatText)
            % Print a log message to the command line
            arguments
                obj
                msg string {mustBeText}
                verboseLevel (1,1) {mustBeInteger} = 0;
                nvargs_formatText.indentLevel (1,1) {mustBeInteger} = 0;
                nvargs_formatText.labelSuffix (1,:) {mustBeTextScalar} = ""
                nvargs_formatText.literal (1,1) logical = false
                nvargs_formatText.wrapText (1,1) logical = true
            end

            if obj.verbose >= verboseLevel
                nvargsCell = namedargs2cell(nvargs_formatText);
                formattedText = obj.formatText(msg, nvargsCell{:});
                disp(formattedText);
            end     
        end
    end

    methods (Access = private, Hidden)
        function formattedText = formatText(obj, text, nvargs)
            % Format text as a log message
            arguments
                obj
                text string {mustBeText}
                nvargs.indentLevel (1,1) {mustBeInteger} = 0;
                nvargs.labelSuffix (1,:) {mustBeTextScalar} = ""
                nvargs.literal (1,1) logical = false
                nvargs.wrapText (1,1) logical = true
                nvargs.gap string {mustBeMember(nvargs.gap,["none","top"])} = "top"
            end
            indentLevel = nvargs.indentLevel;
            labelSuffix = nvargs.labelSuffix;
            literal = nvargs.literal;
            wrapText = nvargs.wrapText;

            % Create the full label
            lbl = obj.label ...
                + labelSuffix ...
                + obj.labelDelimiter ...
                + pad("", obj.labelTextGapSize);
            
            % Get a string to insert as the whitespace before indented text
            indentText = pad( ...
                "", ...
                (obj.baseIndentLevel + indentLevel) * obj.indentSize ...
                );

            % Format the content of the text
            msg = text;
            if ~literal
                msg = compose(text);
            end
            if wrapText
                textWidth = obj.lineWidth ...
                    - strlength(lbl) ...
                    - strlength(indentText);
                msg = string(textwrap(msg, textWidth));
            end
            
            % Create the full output
            formattedText = lbl + indentText + msg;
            formattedText = join(formattedText, newline);

            % Do not print the label on blank lines
            pat = lbl + indentText + ...
                lookAheadBoundary(lineBoundary | textBoundary);
            formattedText = erase(formattedText, pat);

%             formattedText = sprintf("\n%s", formattedText);
        end
    end
end