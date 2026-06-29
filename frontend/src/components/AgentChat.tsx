export default function AgentChat({ log }: { log: string[] }) {
  if (!log.length)
    return <div className="panel-empty">Control-room log appears here.</div>;
  return (
    <div className="chat">
      {log.map((line, i) => {
        const [agent, ...rest] = line.split(":");
        return (
          <div className="chat-line" key={i}>
            <span className="chat-agent">{agent}</span>
            <span className="chat-text">{rest.join(":")}</span>
          </div>
        );
      })}
    </div>
  );
}
