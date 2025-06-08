import React, { useState } from 'react';
import { Clock } from 'lucide-react';

interface Citation {
  text: string;
  time: number;
  timestamp: string;
  citation_id: number;
}

interface FormattedMessageProps {
  content: string;
  citations: Citation[];
  onTimeJump: (time: number) => void;
}

const FormattedMessage: React.FC<FormattedMessageProps> = ({ content, citations, onTimeJump }) => {
  const [hoveredCitation, setHoveredCitation] = useState<number | null>(null);

  const formatText = (text: string): JSX.Element[] => {
    const elements: JSX.Element[] = [];
    let currentIndex = 0;
    
    // Replace timestamp patterns with citation markers
    const timestampPattern = /\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g;
    let match;
    
    while ((match = timestampPattern.exec(text)) !== null) {
      const beforeMatch = text.slice(currentIndex, match.index);
      const timestamp = match[1];
      
      // Add text before the timestamp
      if (beforeMatch) {
        elements.push(...parseMarkdown(beforeMatch, elements.length));
      }
      
      // Find corresponding citation
      const citation = citations.find(c => c.timestamp === timestamp);
      if (citation) {
        elements.push(
          <span
            key={`citation-${elements.length}`}
            className="relative inline-block"
          >
            <button
              className="inline-flex items-center justify-center w-5 h-5 text-xs bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors cursor-pointer ml-1 mr-1 align-super"
              onClick={() => onTimeJump(citation.time)}
              onMouseEnter={() => setHoveredCitation(citation.citation_id)}
              onMouseLeave={() => setHoveredCitation(null)}
              title={`Jump to ${citation.timestamp}`}
            >
              {citation.citation_id}
            </button>
            
            {/* Tooltip */}
            {hoveredCitation === citation.citation_id && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
                <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg max-w-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <Clock className="w-3 h-3" />
                    <span className="font-medium">{citation.timestamp}</span>
                  </div>
                  <p className="text-gray-300">{citation.text}</p>
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            )}
          </span>
        );
      }
      
      currentIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    const remainingText = text.slice(currentIndex);
    if (remainingText) {
      elements.push(...parseMarkdown(remainingText, elements.length));
    }
    
    return elements;
  };

  const parseMarkdown = (text: string, startIndex: number): JSX.Element[] => {
    const elements: JSX.Element[] = [];
    const lines = text.split('\n');
    
    lines.forEach((line, lineIndex) => {
      const key = `line-${startIndex}-${lineIndex}`;
      
      if (line.trim() === '') {
        elements.push(<br key={key} />);
        return;
      }
      
      // Handle headers
      if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
        const headerText = line.slice(2, -2);
        elements.push(
          <h4 key={key} className="font-semibold text-foreground mt-3 mb-2 first:mt-0">
            {headerText}
          </h4>
        );
        return;
      }
      
      // Handle bullet points
      if (line.trim().startsWith('•')) {
        const bulletText = line.trim().slice(1).trim();
        elements.push(
          <div key={key} className="flex items-start gap-2 mb-1">
            <span className="text-muted-foreground mt-1">•</span>
            <span>{parseInlineFormatting(bulletText)}</span>
          </div>
        );
        return;
      }
      
      // Handle numbered lists
      const numberedMatch = line.match(/^\s*(\d+)\.\s+(.+)/);
      if (numberedMatch) {
        const [, number, listText] = numberedMatch;
        elements.push(
          <div key={key} className="flex items-start gap-2 mb-1">
            <span className="text-muted-foreground mt-1 font-medium">{number}.</span>
            <span>{parseInlineFormatting(listText)}</span>
          </div>
        );
        return;
      }
      
      // Regular paragraph
      if (line.trim()) {
        elements.push(
          <p key={key} className="mb-2 leading-relaxed">
            {parseInlineFormatting(line)}
          </p>
        );
      }
    });
    
    return elements;
  };

  const parseInlineFormatting = (text: string): JSX.Element[] => {
    const elements: JSX.Element[] = [];
    let currentIndex = 0;
    
    // Handle bold text **text**
    const boldPattern = /\*\*(.*?)\*\*/g;
    let match;
    
    while ((match = boldPattern.exec(text)) !== null) {
      // Add text before bold
      if (match.index > currentIndex) {
        const beforeText = text.slice(currentIndex, match.index);
        elements.push(<span key={`text-${elements.length}`}>{beforeText}</span>);
      }
      
      // Add bold text
      elements.push(
        <strong key={`bold-${elements.length}`} className="font-semibold">
          {match[1]}
        </strong>
      );
      
      currentIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    if (currentIndex < text.length) {
      elements.push(<span key={`text-${elements.length}`}>{text.slice(currentIndex)}</span>);
    }
    
    return elements;
  };

  return (
    <div className="text-sm leading-relaxed">
      {formatText(content)}
    </div>
  );
};

export default FormattedMessage;
