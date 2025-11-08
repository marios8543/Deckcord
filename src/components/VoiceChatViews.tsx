import { useDeckcordState } from "../hooks/useDeckcordState";

export function VoiceChatChannel() {
  const state = useDeckcordState();
  if (state?.vc == undefined) return (<div></div>);
  return (
    <div style={{ marginTop: "-30px" }}>
      <h3>{state?.vc?.channel_name}</h3>
      <h4 style={{ marginTop: "-20px" }}>{state?.vc?.guild_name}</h4>
    </div>
  );
}

export function VoiceChatMembers() {
  const state = useDeckcordState();
  if (state?.vc?.users == undefined) return (<div></div>);
  const members = [];
  for (const user of state?.vc?.users) {
    members.push(
      <li style={{ display: "flex", justifyContent: "left" }}>
        <img
          src={
            "https://cdn.discordapp.com/avatars/" +
            user?.id +
            "/" +
            user?.avatar +
            ".webp"
          }
          width={32}
          height={32}
        />
        {user?.username}
      </li>
    );
  }
  return <ul style={{ marginTop: "-30px" }}>{members}</ul>;
}
