import React, { useState } from "react";
import JSZip from "jszip";
import Calendar from "./Calendar";
import FileSummarizer from "./FileSummarizer";
import "./Tabs.css";

const Tabs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("calendar");
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState<string | null>(null);
  const [error, setError] = useState<string>("");

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (event.target.files) {
      const selectedFile = event.target.files[0];
      const fileExtension = selectedFile.name.split(".").pop()?.toLowerCase();

      if (fileExtension === "zip" || selectedFile.type === "application/zip") {
        setFile(selectedFile);
        setError(""); // Clear any previous error
        try {
          const extractedText = await extractTextFromZip(selectedFile);
          setExtractedText(extractedText);
        } catch (extractionError) {
          setError("Failed to extract text from the ZIP file.");
        }
      } else {
        setFile(null);
        setExtractedText(null);
        setError("Please upload a ZIP file.");
      }
    }
  };

  const extractTextFromZip = async (file: File): Promise<string> => {
    const zip = new JSZip();
    const content = await zip.loadAsync(file);
    let textContent = "";

    // Loop through files in the ZIP and extract the first .txt file
    for (const fileName in content.files) {
      if (fileName.endsWith(".txt")) {
        textContent = await content.files[fileName].async("text");
        break;
      }
    }

    if (!textContent) {
      throw new Error("No .txt file found in the ZIP.");
    }

    return textContent;
  };

  const handleSummarizeFile = () => {
    if (extractedText) {
      setExtractedText(extractedText); // This triggers summarization
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "calendar":
        return extractedText ? (
          <Calendar text={extractedText} />
        ) : (
          <div>No text available</div>
        );
      case "fileSummarizer":
        return (
          <FileSummarizer
            text={extractedText}
            onSummarize={handleSummarizeFile}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="tabs">
      <div className="file-input">
        <label htmlFor="file-input" className="custom-file-upload">
          Choose File
        </label>
        <input id="file-input" type="file" onChange={handleFileChange} />
        {file && (
          <span className="file-status">File selected: {file.name}</span>
        )}
        {error && <span className="file-error">{error}</span>}
      </div>
      <div className="tab-buttons">
        <button
          className={activeTab === "calendar" ? "active" : ""}
          onClick={() => setActiveTab("calendar")}
        >
          Calendar
        </button>
        <button
          className={activeTab === "fileSummarizer" ? "active" : ""}
          onClick={() => setActiveTab("fileSummarizer")}
        >
          File Summarizer
        </button>
      </div>
      <div className="tab-content">{renderContent()}</div>
    </div>
  );
};

export default Tabs;
