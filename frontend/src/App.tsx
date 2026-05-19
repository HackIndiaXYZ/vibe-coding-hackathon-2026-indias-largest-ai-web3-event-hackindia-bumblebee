import { Routes, Route, Navigate } from "react-router-dom";

import RoleSelect from "./screens/RoleSelect";
import Briefing from "./screens/Briefing";
import Workspace from "./screens/Workspace";
import Scorecard from "./screens/Scorecard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleSelect />} />
      <Route path="/briefing/:sessionId" element={<Briefing />} />
      <Route path="/workspace/:sessionId" element={<Workspace />} />
      <Route path="/scorecard/:sessionId" element={<Scorecard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
