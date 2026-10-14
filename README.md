# Frota-Litoral-Med
Sistema de gestão de frota da Litoral Med — controle de movimentação dos veículos, gestão de documentos e manutenções.

## Acesso pelo GitHub Codespaces

O Codespace inicia o servidor na porta 8000 e encaminha essa porta como pública. Abra a porta **Frota Litoral Med** na aba **Ports** do VS Code e copie o endereço encaminhado para compartilhar com os usuários.

Para manter o mesmo link, use sempre a mesma instância do Codespace: o endereço encaminhado permanece igual quando ela é parada e retomada, mas muda se a instância for excluída e outra for criada. Guarde o link e não exclua o Codespace.

O servidor é iniciado automaticamente quando o Codespace inicia ou é retomado. Se ele for suspenso por inatividade, o sistema fica indisponível até o Codespace ser retomado; portanto, essa opção não oferece acesso contínuo enquanto o Codespace estiver parado. Para acesso contínuo, publique o sistema em uma hospedagem com armazenamento persistente.

O aplicativo exige uma conta de administrador inicial. A primeira pessoa que abrir o sistema pode criar essa conta; depois, o administrador gerencia os demais acessos pela tela de usuários.

## Hospedagem 24 horas (Oracle Cloud Free Tier)

Os arquivos em [`deploy/`](deploy) instalam o sistema em uma VM Ubuntu: Node.js, serviço `systemd` (reinicia sozinho), Caddy na porta 80/443 e backup diário do banco.

1. Crie a instância Ubuntu na Oracle Cloud (shape Always Free) e, na rede (Security List), libere as portas **22, 80 e 443**. Não libere a 8000.
2. Garanta que a versão desejada do código esteja no GitHub (`git push`).
3. Conecte por SSH e execute:

   ```bash
   sudo apt-get update && sudo apt-get install -y git
   git clone https://github.com/edgard2509/Frota-Litoral-Med.git
   sudo bash Frota-Litoral-Med/deploy/setup.sh
   ```

4. Acesse `http://IP_PUBLICO`. Para HTTPS, aponte um domínio para o IP, edite `/etc/caddy/Caddyfile` trocando `:80` pelo domínio e rode `sudo systemctl reload caddy`.

O banco fica em `/var/lib/frota-litoral-med` e os backups diários (14 dias) em `/var/backups/frota-litoral-med`. Para atualizar: `sudo bash /opt/frota-litoral-med/deploy/setup.sh` novamente. Para levar os dados atuais, copie `data/frota.sqlite` (com o servidor parado) para `/var/lib/frota-litoral-med/` mantendo o dono `frota`.
Mantenha o sistema sempre aberto, mesmo com o computador desligado. Considere o link de acesso ao sistema sempre disponível, 7 dias por semana, 24 horas por dia, mesmo sem hospedagem.
