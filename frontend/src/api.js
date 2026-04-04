import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const uploadReferencePDF = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/reference/upload', fd)
}

export const uploadStudentPDFs = (examId, files) => {
  const fd = new FormData()
  files.forEach((file) => fd.append('files', file))
  return api.post(`/exam/${examId}/students/upload`, fd)
}

export const getStatus = (examId) => api.get(`/exam/${examId}/status`)

export const getSummary = (examId) => api.get(`/exam/${examId}/summary`)

export const getQuestionDetail = (examId, qNumber) =>
  api.get(`/exam/${examId}/question/${qNumber}`)

export const getResults = (examId) => api.get(`/exam/${examId}/results`)

export const getExamClusters = (examId) => api.get(`/exam/${examId}/clusters`)

export const getExamMetrics = (examId) => api.get(`/exam/${examId}/metrics`)

export const exportCSVUrl = (examId) => `/api/exam/${examId}/export`

export const gradedPdfUrl = (examId, rollNumber) =>
  `/api/exam/${examId}/student/${encodeURIComponent(rollNumber)}/graded-pdf`

export default api
