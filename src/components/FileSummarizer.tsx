import React from "react";

interface FileSummarizerProps {
  text: string | null;
}

const FileSummarizer: React.FC<FileSummarizerProps> = ({ text }) => {
  if (!text) {
    return (
      <div>Please upload a ZIP file containing a text file to summarize.</div>
    );
  }

  const summarizeText = (text: string): string => {
    return text.split(" ").slice(0, 500).join(" ") + "...";
  };

  const summary = summarizeText(text);

  return (
    <div>
      <h2>Summary:</h2>
      <p>{summary}</p>
    </div>
  );
};

export default FileSummarizer;
