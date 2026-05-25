import { Navigate, Route, Routes } from "react-router-dom";

import TopNav from "./components/TopNav";
import BiasDashboard from "./screens/BiasDashboard";
import Briefing from "./screens/Briefing";
import Disclosure from "./screens/Disclosure";
import Explanation from "./screens/Explanation";
import Landing from "./screens/Landing";
import Library from "./screens/Library";
import PracticeHub from "./screens/PracticeHub";
import RecruiterDashboard from "./screens/RecruiterDashboard";
import RecruiterSession from "./screens/RecruiterSession";
import Rights from "./screens/Rights";
import Scorecard from "./screens/Scorecard";
import SubProcessors from "./screens/SubProcessors";
import Workspace from "./screens/Workspace";

export default function App() {
  return (
    <>
      <TopNav />
      <Routes>
        {/* Candidate flow */}
        <Route path="/" element={<Landing />} />
        <Route path="/practice" element={<PracticeHub />} />
        <Route path="/disclosure/:sessionId" element={<Disclosure />} />
        <Route path="/briefing/:sessionId" element={<Briefing />} />
        <Route path="/workspace/:sessionId" element={<Workspace />} />
        <Route path="/scorecard/:sessionId" element={<Scorecard />} />
        <Route path="/explanation/:sessionId" element={<Explanation />} />

        {/* Recruiter views */}
        <Route path="/recruiter" element={<RecruiterDashboard />} />
        <Route path="/recruiter/:sessionId" element={<RecruiterSession />} />

        {/* Org-level mocks */}
        <Route path="/library" element={<Library />} />
        <Route path="/fairness" element={<BiasDashboard />} />
        <Route path="/rights" element={<Rights />} />
        <Route path="/sub-processors" element={<SubProcessors />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
