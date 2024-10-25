import React, { useState } from "react";
import "./EmailPopup.css";

interface EmailPopupProps {
  onSubmit: (email: string, password: string) => void;
  onClose: () => void;
}

const EmailPopup: React.FC<EmailPopupProps> = ({ onSubmit, onClose }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(email, password);
    onClose();
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
