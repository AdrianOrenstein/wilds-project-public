from typing import Any, Dict, Optional, Tuple

import pytorch_lightning as pl
import torch


class BaseExperiment(pl.LightningModule):
    NAME = "base-experiment"
    TAGS = {}
    TRAINING_KWARGS = {}

    def __init__(
        self,
        **kwargs: Optional[Any],
    ):
        super().__init__()

    def calculate_loss(self, y_hat: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return NotImplementedError

    def step(
        self, batch: Tuple[torch.Tensor, torch.Tensor]
    ) -> Tuple[torch.Tensor, ...]:
        x, y, metadata = batch

        y_hat = self.model(x)
        loss = self.calculate_loss(y_hat, y)
        return x, y, y_hat, metadata, loss

    def training_step(self, batch, batch_idx) -> Dict[str, torch.Tensor]:
        _, y, y_hat, metadata, loss = self.step(batch)
        self.log("1_train/train_loss", loss.item())

        self.log_metrics(y_hat, y, metadata, prefix="1_train", prog_bar=True)

        return {"loss": loss}

    def validation_step(self, batch, batch_idx) -> None:
        _, y, y_hat, metadata, loss = self.step(batch)
        self.log("2_val/val_loss", loss.item())

        self.log_metrics(y_hat, y, metadata, prefix="2_val")

    def test_step(self, batch, batch_idx) -> None:
        _, y, y_hat, metadata, loss = self.step(batch)
        self.log("3_test/test_loss", loss.item())

        self.log_metrics(y_hat, y, metadata, prefix="3_test")

    def log_metrics(
        self,
        y_hat: torch.Tensor,
        y: torch.Tensor,
        metadata: torch.Tensor,
        prefix: str,
        prog_bar: bool = False,
    ) -> None:

        for metric_name, metric_function in self.metrics.items():
            if len(y.unique()) != 1:
                self.log(
                    f"{prefix}/{metric_name}",
                    metric_function(torch.argmax(y_hat, dim=1).cpu(), y.cpu()),
                    prog_bar=prog_bar,
                )

        wilds_metrics, wilds_metrics_str = self.data_module.dataset.eval(
            torch.argmax(y_hat, dim=1).cpu(), y.cpu(), metadata.cpu()
        )

        for metric_name, metric_value in wilds_metrics.items():
            if len(y.unique()) != 1:
                self.log(
                    f"WILDS-{prefix}/{metric_name}",
                    metric_value,
                    prog_bar=prog_bar,
                )

    def configure_optimizers(self):
        opt = torch.optim.Adam(self.parameters(), lr=self.learning_rate, eps=1e-06)

        return {
            "optimizer": opt,
        }
