document.addEventListener("DOMContentLoaded", () => {
  const chatArea = document.getElementById("chat-area");
  const questionInput = document.getElementById("question-input");
  const sendBtn = document.getElementById("send-btn");

  const optionCards = document.querySelectorAll(".option-card");
  const optionLabel = document.getElementById("option-label");

  const uploadSection = document.getElementById("upload-section");

  // File inputs
  const file1 = document.getElementById("uploaded_file1");
  const file2 = document.getElementById("uploaded_file2");

  // Default option
  let currentOption = "1";

  // Make each card clickable
  optionCards.forEach(card => {
    card.addEventListener("click", () => {
      currentOption = card.getAttribute("data-option");
      optionLabel.textContent = currentOption;

      // Option 2 uses stackwalls.txt only, so hide the upload section
      if (currentOption === "2") {
        uploadSection.style.display = "none";
      } else {
        uploadSection.style.display = "block";
      }

      // Optionally, you can clear previous chat or inputs when changing options
      // Uncomment the lines below if desired:
      // chatArea.innerHTML = "";
      // questionInput.value = "";
    });
  });

  // Utility: append a message to chat area
  function appendMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender);
    msgDiv.innerText = text;
    chatArea.appendChild(msgDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  // Handle Send button
  sendBtn.addEventListener("click", async () => {
    const question = questionInput.value.trim();
    if (!question) return;

    // Display user's message in chat
    appendMessage("user", question);

    // Prepare form data
    const formData = new FormData();
    formData.append("username", "anonymous_user");  // or get from a user field
    formData.append("question", question);
    formData.append("option", currentOption);

    // If not option 2, we gather the file uploads
    if (currentOption !== "2") {
      if (file1.files.length > 0) {
        formData.append("uploaded_file1", file1.files[0]);
      }
      if (file2.files.length > 0) {
        formData.append("uploaded_file2", file2.files[0]);
      }
    }

    // Determine the endpoint
    const endpoint = "/api/interactive_chat";

    // Send request to the unified endpoint
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.error) {
        appendMessage("bot", `Error: ${data.error}`);
      } else {
        appendMessage("bot", data.answer || "(No answer provided)");
      }
    } catch (err) {
      console.error("Error calling endpoint:", err);
      appendMessage("bot", "Could not reach the server.");
    }

    // Clear the question input
    questionInput.value = "";
  });
});
