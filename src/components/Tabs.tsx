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
  const [isFetchingEmails, setIsFetchingEmails] = useState<boolean>(false);
  const [isSignedIn, setIsSignedIn] = useState<boolean>(false);
  const [connectedEmail, setConnectedEmail] = useState<string>("");

  const handleSignInOrOut = async () => {
    setError("");

    if (isSignedIn) {
      // Sign out logic
      try {
        const response = await fetch("http://localhost:5000/sign-out", {
          method: "POST",
        });
        if (!response.ok) throw new Error("Failed to sign out.");
        setIsSignedIn(false);
        setConnectedEmail("");
        setExtractedText(null);
      } catch (error) {
        console.error("Error signing out:", error);
        setError("Failed to sign out. Please try again.");
      }
    } else {
      setIsFetchingEmails(true);
      try {
        const response = await fetch("http://localhost:5000/fetch-emails", {
          method: "GET",
        });
        if (!response.ok) {
          throw new Error("Failed to fetch emails.");
        }
        const data = await response.json();
        setIsSignedIn(true);
        setConnectedEmail(data.user_email || "Unknown");
        const emailBodies = data.emailBodies || [];
        if (emailBodies.length > 0) {
          const combinedText = emailBodies.join("\n\n");
          setExtractedText(combinedText);
        } else {
          setExtractedText("No content found in fetched emails.");
        }
      } catch (error) {
        console.error("Error fetching emails:", error);
        setError("Failed to fetch emails. Please try again.");
      } finally {
        setIsFetchingEmails(false);
      }
    }
  };

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
          setExtractedText(extractedText || "No text found in the ZIP file.");
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

  const extractTextFromZip = async (file: File): Promise<string | null> => {
    const zip = new JSZip();
    const content = await zip.loadAsync(file);
    let textContent = "";

    for (const fileName in content.files) {
      if (fileName.endsWith(".txt")) {
        textContent = await content.files[fileName].async("text");
        break;
      }
    }

    return textContent || null;
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
          <div>No tasks available</div>
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
        <div className="button-container">
          <label htmlFor="file-input" className="custom-file-upload">
            Choose File
          </label>
          <input id="file-input" type="file" onChange={handleFileChange} />
          {file && (
            <span className="file-status">File selected: {file.name}</span>
          )}
          {error && <span className="file-error">{error}</span>}
          <button
            className="custom-file-upload" // Match the "Choose File" button styles
            onClick={handleSignInOrOut}
            disabled={isFetchingEmails}
          >
            {isSignedIn ? `Signed in as ${connectedEmail}` : "Sign In"}
          </button>
        </div>
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
          Summarizer
        </button>
      </div>
      <div className="tab-content">{renderContent()}</div>
    </div>
  );
};

export default Tabs;
