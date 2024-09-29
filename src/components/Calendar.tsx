import React, { useEffect, useState } from "react";
import axios from "axios";
import "./Calendar.css";

interface Task {
  time: string;
  title: string;
  date: string;
}

interface CalendarProps {
  text: string; // Text to extract events from
}

const Calendar: React.FC<CalendarProps> = ({ text }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [date, setDate] = useState<string>("");

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await axios.post("http://localhost:5000/events", { text });
        const schedule = response.data.events;

        // Map the events to extract task details (event, date, time)
        const formattedTasks = schedule.map((event: any) => ({
          time: event.Time || "No Time",
          title: event.Event || "No Event",
          date: event.Date || "No Date",
        }));

        setTasks(formattedTasks);

        // If there's a date provided by the events, set it
        if (formattedTasks.length > 0 && formattedTasks[0].date !== "No Date") {
          setDate(formattedTasks[0].date);
        } else {
          // Fallback to a default or current date
          setDate(new Date().toISOString().split('T')[0]);
        }
      } catch (error) {
        console.error("Error fetching events:", error);
      }
    };

    fetchEvents();
  }, [text]);

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
          {tasks.length > 0 ? (
            tasks.map((task, index) => (
              <div key={index} className="task-item">
                <div className="task-time">{task.time}</div>
                <div className="task-title">{task.title}</div>
                <div className="task-date">({task.date})</div> {/* Optionally show the date */}
              </div>
            ))
          ) : (
            <div>No tasks available</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Calendar;
