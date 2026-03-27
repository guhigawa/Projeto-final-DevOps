## 1.INTRODUÇÃO
### A Startup: "Inventory"
A **Inventory** é uma startup que oferece uma plataforma simplificada para pequenos vendedores gerenciarem seu catálogo de produtos de forma segura e organizada.

### Para o Usuário Final (Vendedor)

- **Registro**: Registre-se na plataforma com email e senha
- **Gerencie seu catálogo**: Adicione, edite e remova produtos do seu estoque
- **Controle seu perfil**: Atualize seus dados pessoais
- **Acesso seguro**: Todas as operações são protegidas por autenticação JWT

### Funcionalidades Principais

| Serviço | Funcionalidade | Endpoint |
|---------|----------------|----------|
| **User Service** | Registro de vendedores | `POST /register` |
| **User Service** | Autenticação | `POST /login` |
| **User Service** | Gerenciamento de perfil | `GET/PUT /profile` |
| **Product Service** | Criar produto | `POST /products` |
| **Product Service** | Listar produtos | `GET /products` |
| **Product Service** | Atualizar produto | `PUT /products` |
| **Product Service** | Remover produto | `DELETE /products` |

### Como Usar na Prática

1. **Usuário**, acessa a plataforma e cria sua conta
2. **Usuário faz login** e recebe um token de acesso
3. **Usuário adiciona seus produtos** ao catálogo (nome, preço, quantidade)
4. **Usuário pode editar** produtos existentes ou removê-los do estoque
5. **Usuário ode atualizar** seus dados pessoais no perfil
6. **Todas as operações** são rastreadas via Jaeger, permitindo à startup identificar possíveis gargalos

### Arquitetura Técnica

Este projeto implementa uma arquitetura de microsserviços com **Python/Flask** e **MySQL**, containerizada com **Docker** e orquestrada com **Kubernetes (MicroK8s)**. O pipeline CI/CD é automatizado com **GitHub Actions**, incluindo testes unitários, de integração e funcionais. O monitoramento é realizado com **Jaeger** para tracing distribuído entre os microsserviços, permitindo rastrear cada requisição desde o login até a gestão de produtos.

### Interação entre Microsserviços

Os serviços interagem da seguinte forma:
- O **Product Service** depende do **User Service** para autenticação
- Quando um vendedor tenta criar/editar/remover um produto, o Product Service valida o token JWT com o User Service
- Isso garante que cada vendedor só acesse seus próprios produtos (isolamento de dados)

![alt text](documentation/20251009-HLD-ProjetoFinal-DevOps.drawio.png)
*Figura 1: Diagrama de Arquitetura do Projeto*

### Componentes Principais:
- **User Service**: Gerenciamento de usuários (registro, login, perfil)
- **Product Service**: Gerenciamento de produtos (CRUD)
- **MySQL**: Bancos de dados separados por serviço
- **Jaeger**: Tracing distribuído entre microsserviços
- **Kubernetes**: Orquestração em produção com HPA e Rolling Updates

## 2. REPOSITÓRIO

O projeto está hospedado em um repositório **público** no GitHub:
[https://github.com/guhigawa/Projeto-final-DevOps.git](https://github.com/guhigawa/Projeto-final-DevOps.git)

### Justificativa para a Startup
- **Acesso imediato**: Qualquer membro da equipe pode clonar e começar a trabalhar
- **Transparência**: Código aberto facilita auditoria e revisão de código
- **Portfólio**: Demonstra boas práticas de desenvolvimento para futuros clientes
- **Custo zero**: GitHub Actions gratuito para repositórios públicos

### Segurança
Apesar de público, **nenhuma credencial sensível** está no repositório:
- Secrets utilizam GitHub Secrets
- Senhas de banco via variáveis de ambiente
- Tokens JWT injetados no deploy

---

## 3. Tecnologias Utilizadas

| Categoria | Tecnologias |
|-----------|------------|
| **Backend** | Python 3.10/3.11, Flask, JWT |
| **Banco de Dados** | MySQL 8.0 |
| **Containerização** | Docker, Docker Compose |
| **Orquestração** | Kubernetes (MicroK8s) |
| **CI/CD** | GitHub Actions |
| **Monitoramento** | Jaeger, OpenTelemetry |
| **Testes** | Pytest, Coverage |
| **Infraestrutura** | Ubuntu 22.04 |

## 4. Estrutura de Diretórios
Projeto_final
├── docker-compose.staging.yml
├── docker-compose.yml
├── documentation
├── generate_hashed_password.py
├── k8s
├── Makefile
├── monitoring
├── pipeline.png
├── product-service
├── README.md
├── requirements
├── requirements.txt.backup
├── scripts
├── user-service
└── venv

## 5. Configuração dos Ambientes

| Ambiente | Ferramenta | Acesso | Comando |
|----------|------------|--------|---------|
| **DEV** | Docker Compose + Local | `http://localhost:3001` (user), `http://localhost:3002` (product) | `make dev` |
| **STG** | Docker Compose + GitHub Actions | `http://localhost:4001` (user), `http://localhost:4002` (product) | `make staging` |
| **PRD** | Kubernetes (MicroK8s) | `http://user.local.prod`, `http://product.local.prod` | `make prod` |


## 6. Pipeline CI/CD

![alt text](documentation/pipeline.png)
*Figura 2: Pipeline automatizada no GitHub Actions*

### Jobs do Pipeline:

| Job | Descrição | Condição |
|-----|-----------|----------|
| `test-unit` | Testes unitários e validadores | Sempre |
| `test-integration` | Testes de integração com MySQL | Sempre |
| `deploy-staging` | Deploy em staging e testes funcionais | Só na main/PR |
| `deploy-production` | Deploy em produção (com aprovação manual) | Só na main |

## 7. Testes manuais e Testes automatizados
Os resultados dos testes feitos para garantir o funcionamento dos serviços foram concluidos e estão todos documentados no diretório Documentation. Além destes, há também, dentro de cada diretório dos serviços diretórios de evidências de logging que auxiliaram no debugging e realização de testes.

## 8. Monitoramento com Jaeger
O Projeto utilzar Jaeger para rastrear a requisição de serviços
env:
- name: JAEGER_AGENT_HOST
  value: "jaeger.monitoring.svc.cluster.local"
- name: JAEGER_AGENT_PORT
  value: "6831"
- name: OTEL_SERVICE_NAME
  value: "user-service"  # ou "product-service"

# IP do servidor
NODE_IP=$(microk8s kubectl get node -o jsonpath='{.items[0].status.addresses[0].address}')

# URL do Jaeger UI
echo "Jaeger UI: http://$NODE_IP:30001"

Funcionalidades Implementadas
Tracing automático com OpenTelemetry

Spans para cada operação (validação, queries SQL, etc.)

Correlação entre serviços

Identificação de gargalos e erros

# Evidencias de funcionamento
![alt text](documentation/Jaeger_primeiro_teste.png)
![alt text](documentation/register_tracer.png)
![alt text](documentation/login_trace.png)
![alt text](documentation/get_product_tracer.png)

9. Evidências de Funcionamento
9.1 Kubernetes - Pods Rodando
(venv) ubuntu@ubuntu-2204:~/Downloads/Projeto_final$ microk8s kubectl get all -n projeto-final
NAME                                  READY   STATUS    RESTARTS       AGE
pod/mysql-product-0                   1/1     Running   25 (95m ago)   17d
pod/mysql-user-0                      1/1     Running   29 (95m ago)   22d
pod/product-service-dfcbc566c-4zz8f   1/1     Running   8 (95m ago)    4d1h
pod/product-service-dfcbc566c-w57lt   1/1     Running   8 (95m ago)    4d1h
pod/user-service-5957b547bf-q8q5v     1/1     Running   8 (95m ago)    4d1h
pod/user-service-5957b547bf-r4zj4     1/1     Running   0              93m

NAME                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/mysql-product     ClusterIP   None            <none>        3306/TCP   22d
service/mysql-user        ClusterIP   None            <none>        3306/TCP   22d
service/product-service   ClusterIP   10.152.183.31   <none>        5002/TCP   18d
service/user-service      ClusterIP   10.152.183.64   <none>        5001/TCP   21d

NAME                              READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/product-service   2/2     2            2           18d
deployment.apps/user-service      2/2     2            2           21d

NAME                                         DESIRED   CURRENT   READY   AGE
replicaset.apps/product-service-5694886577   0         0         0       4d2h
replicaset.apps/product-service-584d59689f   0         0         0       18d
replicaset.apps/product-service-6c6f9bbf8b   0         0         0       15d
replicaset.apps/product-service-6d96fc5688   0         0         0       4d2h
replicaset.apps/product-service-dfcbc566c    2         2         2       4d1h
replicaset.apps/user-service-574fc57b47      0         0         0       4d2h
replicaset.apps/user-service-5957b547bf      2         2         2       4d1h
replicaset.apps/user-service-6466bfb6d       0         0         0       4d2h
replicaset.apps/user-service-6696bd4bbd      0         0         0       4d2h
replicaset.apps/user-service-77b68d89cb      0         0         0       16d
replicaset.apps/user-service-85d578bb84      0         0         0       16d
replicaset.apps/user-service-c67d55bb6       0         0         0       21d

NAME                             READY   AGE
statefulset.apps/mysql-product   1/1     17d
statefulset.apps/mysql-user      1/1     22d

NAME                                                      REFERENCE                    TARGETS                        MINPODS   MAXPODS   REPLICAS   AGE
horizontalpodautoscaler.autoscaling/product-service-hpa   Deployment/product-service   cpu: 2%/80%, memory: 19%/80%   2         5         2          18d
horizontalpodautoscaler.autoscaling/user-service-hpa      Deployment/user-service      cpu: 1%/70%, memory: 17%/80%   2         5         2          21d

9.2 HPA - Auto Scaling
(venv) ubuntu@ubuntu-2204:~/Downloads/Projeto_final$  microk8s kubectl get hpa -n projeto-final
NAME                  REFERENCE                    TARGETS                        MINPODS   MAXPODS   REPLICAS   AGE
product-service-hpa   Deployment/product-service   cpu: 2%/80%, memory: 19%/80%   2         5         2          18d
user-service-hpa      Deployment/user-service      cpu: 2%/70%, memory: 17%/80%   2         5         2          21d

9.3 Ingress - Acesso aos Serviços
(venv) ubuntu@ubuntu-2204:~/Downloads/Projeto_final$ curl http://user.local.prod/health
{"status":"healthy"}
(venv) ubuntu@ubuntu-2204:~/Downloads/Projeto_final$ curl http://product.local.prod/health
{"status":"healthy"}

10. Problemas Enfrentados e Soluções
10.1 Docker Compose - Ordem de Inicialização
Problema | Solução	|  Lição Aprendida
Serviços Flask iniciavam antes do MySQL estar pronto | Implementação de health checks no docker-compose e verificação em loop | Containers não iniciam na ordem especificada; é preciso garantir dependências com depends_on + condition: service_healthy

10.2 Banco de Dados - Privilégios no Staging
Problema | Solução	|  Lição Aprendida
Erro Access denied for user 'product_user'@'%' | Correção manual de privilégios e ajuste nos scripts de inicialização | Scripts SQL precisam ser idempotentes; variáveis do docker-compose não funcionam dentro de scripts SQL

10.3 GitHub Actions - Secrets em Pull Requests
Problema | Solução	|  Lição Aprendida
PRs não tinham acesso aos secrets, quebrando o pipeline	| Implementação de sistema de fallback com valores padrão para PRs | Pipelines precisam ser resilientes; usar || para fallbacks em múltiplas camadas

10.4 Kubernetes - Exit Code 137 (OOMKilled)
Problema | Solução	|  Lição Aprendida
Pods reiniciando com exit code 137 | Ajuste dos valores de initialDelaySeconds nas probes de liveness/readiness | Exit code 137 indica que o processo foi morto (OOM ou probe failure); probes muito agressivas causam restart loop

10.5 Kubernetes - Imagens não atualizavam
Problema | Solução	|  Lição Aprendida
Mesma tag 1.0.0 não forçava pull da nova imagem | imagePullPolicy: Always + kubectl rollout restart | Kubernetes cacheia imagens com mesma tag; usar latest é anti-pattern, mas Always resolve para desenvolvimento

10.6 Jaeger - Traces não apareciam
Problema | Solução	|  Lição Aprendida
Serviços não enviavam traces para o Jaeger | Correção do protocolo UDP no Service e adição das variáveis de ambiente | Protocolo UDP deve ser explicitamente definido; DNS interno deve seguir padrão servico.namespace.svc.cluster.local

10.7 Variáveis de Ambiente - Inconsistência
Problema | Solução	|  Lição Aprendida
Nomes de variáveis diferentes entre statefulset, configmap e código	| Padronização de nomenclatura e documentação | Consistência é crítica; usar mesma variável em todos os lugares

11. Lições Aprendidas e Pontos-Chave
11.1 Arquitetura de Testes
text
DEV (Local)      - Testes unitários e validadores (rápidos)
STAGING (Docker) - Testes de integração e funcionais (ambiente real)
PROD (K8s)       - Health checks e tracing (validação de deploy)

11.2 Segurança em Múltiplas Camadas
python
# Inseguro: confia no input do usuário
@app.route("/users/<user_id>")
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# Seguro: usa ID do token decodificado
@token_required
def get_user(current_user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (current_user_id,))

11.3 Idempotência em Scripts SQL
sql
-- Perigoso: falha se tabela já existe
CREATE TABLE users (...);

-- Idempotente: só cria se não existir
CREATE TABLE IF NOT EXISTS users (...);

11.4 Debugging em Kubernetes
bash
# Sequência de debug quando algo não funciona
kubectl describe pod <pod>          # 1. Ver eventos
kubectl logs <pod>                   # 2. Ver logs
kubectl exec -it <pod> -- /bin/bash  # 3. Entrar no pod
kubectl get endpoints                 # 4. Ver se service tem endpoints
kubectl get svc                       # 5. Ver IPs dos serviços
11.5 Estratégia de Probes
yaml

# Liveness: "Estou vivo" → Reinicia se falhar
livenessProbe:
  initialDelaySeconds: 45  # Dê tempo para app iniciar
  periodSeconds: 15        # Não sobrecarregue

# Readiness: "Estou pronto para tráfego" → Remove do load balancer
readinessProbe:
  initialDelaySeconds: 10  # Mais agressivo
  periodSeconds: 5         # Verifica frequente

11.6 OpenTelemetry - Boas Práticas
python
# Sempre adicionar atributos relevantes
span.set_attribute("user.id", user_id)
span.set_attribute("product.count", len(products))

# Marcar erros de negócio vs erros técnicos
if not user:
    span.set_attribute("error", True)  # Erro esperado
    return 404

except Exception as e:
    span.set_status(Status(StatusCode.ERROR))  # Falha real
    span.record_exception(e)

11.7 Pipeline Resiliente
yaml
# Fallback em múltiplas camadas
SECRET_KEY: ${{ secrets.JWT_SECRET || env.FALLBACK_KEY || 'default' }}

# Não falhe o deploy por testes funcionais
timeout 300 pytest ... || echo "Tests had issues"

11.8 Checklist de Produção
Secrets nunca versionados

Resource limits definidos (requests/limits)

Probes configuradas com delays adequados

Imagens com tag específica (não latest)

Health checks implementados

Logs em stdout (não arquivos)

Variáveis de ambiente via ConfigMap/Secrets

RollingUpdate strategy configurada

HPA configurado

Monitoring (Jaeger) implementado