from yardstick_benchmark.base import Game
import ansible_runner

class VanillaMC(Game):
    def __init__(self, nodes):
        super().__init__(nodes)
        self.wd = "/var/scratch/{os.getlogin()}/vanillamc"  
        self.template = "templates/server.properties.j2"  
        self.playbook_dir = "games/minecraft/server/J1164"  
        self.jar = "minecraft_server-1.20.1.jar" 

    def deploy(self):
        extra_vars = {
            "wd": self.wd,
            "vanillamc_template": self.template,
            # Add other vars like version, etc., if needed for the template
        }
        
        ansible_runner.run(
            playbook=f"{self.playbook_dir}/vanilla_deploy.yml",
            inventory=self.nodes,  # Or however hosts are passed
            extravars=extra_vars
        )

    def start(self):
        extra_vars = {
            "wd": self.wd,
        }
        ansible_runner.run(
            playbook=f"{self.playbook_dir}/vanilla_start.yml",  
            inventory=self.nodes,
            extravars=extra_vars
        )

    def stop(self):
        extra_vars = {
            "wd": self.wd,
        }
        ansible_runner.run(
            playbook=f"{self.playbook_dir}/vanilla_stop.yml",
            inventory=self.nodes,
            extravars=extra_vars
        )

    def cleanup(self):
        
        pass  # Or ansible_runner.run(playbook=f"{self.playbook_dir}/vanilla_cleanup.yml") 