import axios from 'axios';

export const sendPromptToGPT = async (message) => {
  try {
    const response = await axios.post('http://localhost:8000/api/gpt/chat/', {
      message: message,
    });
    return response.data.response;
  } catch (error) {
    console.error("Error talking to GPT:", error);
    return "Something went wrong. Please try again.";
  }
};
