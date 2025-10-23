import { useState } from 'react'
import { Sparkles, Calendar, Clock, MapPin, Loader2, Star, TrendingUp, Users } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Button } from './components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card.jsx'
import { Input } from './components/ui/input.jsx'
import { Label } from './components/ui/label.jsx'
import './App.css'

function App() {
  const [formData, setFormData] = useState({
    name: '',
    birth_date: '',
    birth_time: '',
    latitude: '',
    longitude: ''
  })

  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const dataToSend = { ...formData }
      if (dataToSend.birth_time && dataToSend.birth_time.length === 5) {
        dataToSend.birth_time += ':00'
      }

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(dataToSend)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Erro ao processar a análise')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

  return (
    <div className="app">
      <div className="app-container">
        <div className="app-header fade-in">
          <div className="app-header-icon">
            <Sparkles className="icon-xxl" />
          </div>
          <h1 className="app-title">Astro Profissões</h1>
          <p className="app-subtitle">
            Descubra sua vocação profissional através da astrologia e inteligência artificial
          </p>
        </div>

        {!results && (
          <Card className="form-card slide-up">
            <CardHeader>
              <CardTitle>Dados de Nascimento</CardTitle>
              <CardDescription>
                Preencha suas informações para gerar sua análise astrológica personalizada
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="form">
                <div className="form-grid">
                  <div className="form-field">
                    <Label htmlFor="name">Nome Completo</Label>
                    <Input
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Seu nome"
                      required
                    />
                  </div>

                  <div className="form-field">
                    <Label htmlFor="birth_date" className="field-label">
                      <Calendar className="icon-sm" />
                      Data de Nascimento
                    </Label>
                    <Input
                      id="birth_date"
                      name="birth_date"
                      type="date"
                      value={formData.birth_date}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="form-field">
                    <Label htmlFor="birth_time" className="field-label">
                      <Clock className="icon-sm" />
                      Hora de Nascimento
                    </Label>
                    <Input
                      id="birth_time"
                      name="birth_time"
                      type="time"
                      value={formData.birth_time}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="form-field">
                    <Label htmlFor="latitude" className="field-label">
                      <MapPin className="icon-sm" />
                      Latitude
                    </Label>
                    <Input
                      id="latitude"
                      name="latitude"
                      type="number"
                      step="any"
                      value={formData.latitude}
                      onChange={handleInputChange}
                      placeholder="-23.5505"
                      required
                    />
                  </div>

                  <div className="form-field form-field-wide">
                    <Label htmlFor="longitude">Longitude</Label>
                    <Input
                      id="longitude"
                      name="longitude"
                      type="number"
                      step="any"
                      value={formData.longitude}
                      onChange={handleInputChange}
                      placeholder="-46.6333"
                      required
                    />
                  </div>
                </div>

                {error && (
                  <div className="error-box">{error}</div>
                )}

                <Button type="submit" className="primary-button" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="icon-spin" />
                      Analisando seu mapa astral...
                    </>
                  ) : (
                    <>
                      <Sparkles className="icon-sm" />
                      Descobrir Minha Vocação
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {results && (
          <div className="results fade-in">
            <Card className="result-card">
              <CardHeader>
                <CardTitle className="result-title">
                  <TrendingUp className="icon-md trend-icon" />
                  Previsões de Profissões
                </CardTitle>
                <CardDescription>
                  Baseado nas características do seu mapa astral
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="predictions-list">
                  {results.predictions.map((pred, index) => (
                    <div key={index} className="prediction-item">
                      <div className="prediction-info">
                        <div className={`prediction-rank rank-${index + 1}`}>
                          {index + 1}
                        </div>
                        <div>
                          <p className="prediction-profession">{pred.profession}</p>
                          <p className="prediction-confidence">
                            Confiança: {pred.confidence === 'high' ? 'Alta' : pred.confidence === 'medium' ? 'Média' : 'Baixa'}
                          </p>
                        </div>
                      </div>
                      <div className="prediction-score">
                        <p>{(pred.probability * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={results.predictions}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="profession"
                        angle={-35}
                        textAnchor="end"
                        height={80}
                        fontSize={12}
                      />
                      <YAxis
                        label={{ value: 'Probabilidade (%)', angle: -90, position: 'insideLeft', offset: 10 }}
                      />
                      <Tooltip formatter={(value) => `${(value * 100).toFixed(1)}%`} labelStyle={{ color: '#1f2937' }} />
                      <Bar dataKey="probability" radius={[10, 10, 0, 0]}>
                        {results.predictions.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="result-card">
              <CardHeader>
                <CardTitle className="result-title">
                  <Star className="icon-md star-icon" />
                  Interpretação Astrológica
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="interpretation">
                  <div className="interpretation-summary">
                    <p>{results.interpretation.summary}</p>
                  </div>

                  <div>
                    <h3 className="interpretation-heading">Fatores Chave:</h3>
                    <ul className="interpretation-list">
                      {results.interpretation.key_factors.map((factor, index) => (
                        <li key={index} className="interpretation-item">
                          <Star className="icon-sm star-icon" />
                          <span>{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="result-card">
              <CardHeader>
                <CardTitle className="result-title">
                  <Users className="icon-md users-icon" />
                  Perfis Similares
                </CardTitle>
                <CardDescription>
                  Personalidades famosas com mapas astrais semelhantes ao seu
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="profiles-grid">
                  {results.similar_profiles.map((profile, index) => (
                    <div key={index} className="profile-card">
                      <h4 className="profile-name">{profile.name}</h4>
                      <p className="profile-profession">{profile.profession}</p>
                      <div className="profile-progress">
                        <div className="progress-track">
                          <div className="progress-bar" style={{ width: `${profile.similarity * 100}%` }}></div>
                        </div>
                        <span className="progress-value">{(profile.similarity * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="actions">
              <Button
                onClick={() => {
                  setResults(null)
                  setFormData({
                    name: '',
                    birth_date: '',
                    birth_time: '',
                    latitude: '',
                    longitude: ''
                  })
                }}
                className="secondary-button"
              >
                Nova Análise
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
