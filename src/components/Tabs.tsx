import React, { useState } from "react";
import JSZip from "jszip";
import Calendar from "./Calendar";
import FileSummarizer from "./FileSummarizer";
import EmailPopup from "./EmailPopup"; // Import EmailPopup
import "./Tabs.css";

const Tabs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("calendar");
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const [showEmailPopup, setShowEmailPopup] = useState<boolean>(false); // New state

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    // Existing file handling code
  };

  const handleEmailSubmit = (email: string, password: string) => {
    console.log("Email:", email, "Password:", password);
    // Implement email fetching logic here
    setShowEmailPopup(false);
  };

  const handleSummarizeFile = () => {
    if (extractedText) {
      setExtractedText(extractedText);
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
        <button
          className="email-button"
          onClick={() => setShowEmailPopup(true)}
        >
          Use Email
        </button>
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

      {showEmailPopup && (
        <EmailPopup
          onSubmit={handleEmailSubmit}
          onClose={() => setShowEmailPopup(false)}
        />
      )}
    </div>
  );
};

export default Tabs;
