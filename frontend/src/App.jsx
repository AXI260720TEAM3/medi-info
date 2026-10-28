import { Route, Routes } from 'react-router'
import DrugSearch from './pages/DrugSearch'

function App(){
  return (
    <Routes>
      <Route path="/drugs" element={<DrugSearch />} />
    </Routes>
  )
}
export default App