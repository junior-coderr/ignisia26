import { BrowserRouter, Routes, Route } from 'react-router-dom'
import UploadScreen from './screens/UploadScreen'
import DashboardScreen from './screens/DashboardScreen'
import ExportScreen from './screens/ExportScreen'
import ClusterScreen from './screens/ClusterScreen'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadScreen />} />
        <Route path="/dashboard/:examId" element={<DashboardScreen />} />
        <Route path="/export/:examId" element={<ExportScreen />} />
        <Route path="/clusters/:examId" element={<ClusterScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
