import React, { useEffect, useState } from "react";
import axios from "axios";
import { format } from "date-fns";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import "./Calendar.css";

interface Task {
  time: string;
  title: string;
  date: string;
}

interface CalendarProps {
  text: string;
}

const Calendar: React.FC<CalendarProps> = ({ text }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [groupedTasks, setGroupedTasks] = useState<{ [key: string]: Task[] }>(
    {}
  );
  const [expandedDates, setExpandedDates] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const addEventsToGoogleCalendar = async () => {
    try {
      if (tasks.length === 0) {
        alert("No tasks to add to Google Calendar.");
        return;
      }

      // Call the backend to add events
      const response = await axios.post("http://localhost:5000/add-events", {
        events: tasks,
      });

      if (response.status === 200) {
        alert("Events successfully added to Google Calendar!");
      } else {
        alert("Failed to add events. Please try again.");
      }
    } catch (error) {
      console.error("Error adding events to Google Calendar:", error);
      alert("An error occurred while adding events.");
    }
  };

  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      try {
        const response = await axios.post("http://localhost:5000/events", {
          text,
        });
        console.log("Response data:", response.data);
        const schedule = response.data.events || [];

        const formattedTasks = schedule.map((event: any) => ({
          time: event.Time || "No Time",
          title: event.Event || "No Event",
          date: event.Date || "No Date",
        }));

        setTasks(formattedTasks);

        const grouped = formattedTasks.reduce((acc: any, task: Task) => {
          const taskDate = task.date || "No Date";
          if (!acc[taskDate]) {
            acc[taskDate] = [];
          }
          acc[taskDate].push(task);
          return acc;
        }, {});

        console.log("Grouped tasks:", grouped); // Check the grouped structure
        setGroupedTasks(grouped);
      } catch (error) {
        console.error("Error fetching events:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [text]);

  const toggleDateExpansion = (date: string) => {
    if (expandedDates.includes(date)) {
      setExpandedDates(expandedDates.filter((d) => d !== date));
    } else {
      setExpandedDates([...expandedDates, date]);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString || dateString === "No Date") {
      return "No Date";
    }

    try {
      const parts = dateString.split("-");
      if (parts.length === 3) {
        const day = parts[0];
        const month = parts[1];
        const year = `20${parts[2]}`;

        const formattedDateString = `${year}-${month}-${day}`;
        const parsedDate = new Date(formattedDateString);

        if (isNaN(parsedDate.getTime())) {
          return "Invalid Date";
        }

        return format(parsedDate, "EEEE, d MMMM, yyyy");
      }

      return "Invalid Date Format";
    } catch (error) {
      return "Invalid Date";
    }
  };

  return (
    <div className="container">
      {loading ? (
        <div className="loading">Loading events...</div>
      ) : Object.keys(groupedTasks).length > 0 ? (
        <>
          <div className="calendar-actions">
            <button
              className="add-to-calendar-btn"
              onClick={addEventsToGoogleCalendar}
            >
              Add to Google Calendar
            </button>
          </div>
          {Object.keys(groupedTasks).map((date, index) => (
            <div key={index} className="date-group">
              <div
                className="date-header"
                onClick={() => toggleDateExpansion(date)}
              >
                <h3>{formatDate(date)}</h3>
                <ChevronDownIcon
                  className={`arrow-icon ${
                    expandedDates.includes(date) ? "open" : ""
                  }`}
                  style={{ width: "16px", height: "16px" }}
                />
              </div>
              {expandedDates.includes(date) && (
                <div className="tasks-list">
                  {groupedTasks[date].map((task, idx) => (
                    <div key={idx} className="task-item">
                      <div className="task-title">{task.title}</div>
                      <div className="task-time">{task.time}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </>
      ) : (
        <div>No tasks available</div>
      )}
    </div>
  );
};

export default Calendar;
