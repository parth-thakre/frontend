import React, { useState } from "react";
import "./EmailPopup.css";
import axios from "axios";
interface EmailPopupProps {
  onSubmit: (emailBodies: string[]) => void;
  onClose: () => void;
}

const EmailPopup: React.FC<EmailPopupProps> = ({ onSubmit, onClose }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await axios.get("http://localhost:5000/fetch-emails");
      const emailBodies = response.data.emails.map(
        (email: { body: string }) => email.body
      );
      console.log("Fetched email bodies:", emailBodies); // Debugging log
      onSubmit(emailBodies); // Pass array of email bodies
    } catch (error) {
      console.error("An error occurred:", error);
      alert("Failed to get emails");
    }
  };

  return (
    <div className="email-popup">
      <div className="popup-content">
        <h2>Enter Email Credentials</h2>
        <form onSubmit={handleSubmit}>
          <label>
            Email:
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="Enter your email"
            />
          </label>
          <label>
            Password:
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
            />
          </label>
          <button type="submit">Submit</button>
          <button type="button" onClick={onClose}>
            Cancel
          </button>
        </form>
      </div>
    </div>
  );
};

export default EmailPopup;
