export const executeStream = async (prompt, quality, onEvent, onError, onComplete) => {
  try {
    const response = await fetch("http://127.0.0.1:8000/execute/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt, quality }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.trim().startsWith('data:')) {
          const dataStr = line.replace(/^data:\s*/, '').trim();
          if (!dataStr) continue;
          
          try {
            const parsed = JSON.parse(dataStr);
            onEvent(parsed);
          } catch (e) {
            console.error("JSON Parse Error:", e, "Raw string:", dataStr);
          }
        }
      }
    }
    onComplete();
  } catch (error) {
    onError(error);
  }
};