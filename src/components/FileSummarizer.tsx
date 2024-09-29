import React, { useState, useEffect } from "react";

interface FileSummarizerProps {
  text: string | null;
  onSummarize: () => void;
}

const FileSummarizer: React.FC<FileSummarizerProps> = ({ text, onSummarize }) => {
  const [summary, setSummary] = useState<string>("");

  useEffect(() => {
    if (text) {
      summarizeText(text);
    }
  }, [text]);

  const summarizeText = async (text: string) => {
    try {
      const response = await fetch("http://localhost:5000/summarize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error("Network response was not ok.");
      }

      const result = await response.json();
      setSummary(result.summary);
    } catch (error) {
      console.error("Error fetching summary:", error);
      setSummary("Error summarizing the text.");
    }
  };

  if (!text) {
    return <div>Please upload a ZIP file containing a text file to summarize.</div>;
  }

  return (
    <div>
      <h2>Summary:</h2>
      <p>{summary}</p>
      <button onClick={onSummarize}>Summarize Text</button>
    </div>
  );
};

export default FileSummarizer;
