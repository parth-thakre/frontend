import React, { useState } from "react";
import "./Calendar.css";

interface Task {
  time: string;
  title: string;
}

const Calendar: React.FC = () => {
  const [date, setDate] = useState<string>("2024-08-26");
  const [tasks, setTasks] = useState<Task[]>([
    { time: "09:00 AM", title: "Morning Meeting" },
    { time: "11:00 AM", title: "Project Update" },
    { time: "01:00 PM", title: "Lunch with Team" },
    { time: "03:00 PM", title: "Client Call" },
    { time: "05:00 PM", title: "Wrap-up and Review" },
  ]);

  return (
    <div className="container">
      <div className="single-day-calendar">
        <div className="calendar-header">
          <h2>
            {new Date(date).toLocaleDateString("en-US", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </h2>
        </div>
        <div className="tasks-list">
          {tasks.map((task, index) => (
            <div key={index} className="task-item">
              <div className="task-time">{task.time}</div>
              <div className="task-title">{task.title}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Calendar;
